import json
import os
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
from pydantic import ValidationError
from catalog import config, utils
from catalog.models import AssessmentModel
from catalog.utils import logger


class SHLParser:
    """
    Parser class that extracts metadata from raw HTML pages of SHL individual test solutions,
    normalizes the attributes, validates them with Pydantic, and saves the output.
    Supports smart fallback text scanning to extract data from live marketing pages.
    """

    def clean_boolean(self, value_str: Optional[str]) -> Optional[bool]:
        """Converts text values (e.g. 'Yes', 'No', 'True', 'False') to boolean or None."""
        if not value_str:
            return None
        
        s = value_str.lower().strip()
        if s in ["yes", "true", "y", "1", "enabled"]:
            return True
        if s in ["no", "false", "n", "0", "disabled"]:
            return False
        return None

    def extract_list_from_ul(self, container: Optional[BeautifulSoup]) -> List[str]:
        """Extracts text from all <li> elements inside a container element."""
        if not container:
            return []
        
        items = []
        for li in container.find_all("li"):
            items.append(li.get_text())
            
        return utils.clean_list(items)

    def parse_html_content(self, html_content: str, url: str) -> Optional[AssessmentModel]:
        """
        Parses raw HTML string and builds a validated AssessmentModel instance.
        Employs robust text-scanning fallback heuristics for live marketing pages.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove script and style elements to avoid extracting code text
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get clean body text for keyword scanning
        body_text = soup.get_text()
        
        # 1. Extract Name
        name_elem = soup.find(id="test-name") or soup.find("h1")
        if name_elem:
            name = utils.clean_text(name_elem.get_text())
        else:
            title_elem = soup.find("title")
            if title_elem:
                # Strip common marketing title suffixes
                title_txt = title_elem.get_text()
                for suffix in ["| SHL", "- SHL", "| Talent Solutions", "- Talent Solutions"]:
                    if suffix in title_txt:
                        title_txt = title_txt.split(suffix)[0]
                name = utils.clean_text(title_txt)
            else:
                # Fall back to deriving from URL slug
                slug = [p for p in url.strip("/").split("/") if p][-1]
                name = slug.replace("-", " ").title()
                
        if not name:
            name = "SHL Assessment Solution"

        # Remove "SHL" or "Test" prefix/suffix formatting if redundant, but keep general name
        name = name.strip()

        # 2. Extract ID Slug
        assessment_id = utils.generate_slug_id(name)

        # 3. Extract Category
        cat_elem = soup.find(id="test-category") or soup.find(class_="product-category")
        category = utils.clean_text(cat_elem.get_text()) if cat_elem else None
        
        if not category:
            # Fall back to URL or name based heuristics
            url_lower = url.lower()
            name_lower = name.lower()
            if "personality" in url_lower or "personality" in name_lower or "motivation" in name_lower:
                category = "Personality & Behavior"
            elif "behavioral" in url_lower or "behavioral" in name_lower or "situational" in name_lower or "judgement" in name_lower:
                category = "Personality & Behavior"
            elif "cognitive" in url_lower or "cognitive" in name_lower or "verify" in name_lower or "reasoning" in name_lower:
                category = "Cognitive Ability"
            elif "skills" in url_lower or "skills" in name_lower or "coding" in name_lower or "simulation" in name_lower:
                category = "Technical Skills"
            else:
                category = "Talent Assessment"

        # 4. Extract Description
        desc_elem = soup.find(id="test-description") or soup.find(class_="product-description")
        description = utils.clean_text(desc_elem.get_text()) if desc_elem else ""
        
        if not description:
            # Try meta description tags
            meta_desc = (
                soup.find("meta", attrs={"name": "description"}) 
                or soup.find("meta", attrs={"property": "og:description"})
                or soup.find("meta", attrs={"name": "twitter:description"})
            )
            if meta_desc:
                description = utils.clean_text(meta_desc.get("content", ""))
                
        if not description:
            # Try to grab the first substantial paragraph
            for p in soup.find_all("p"):
                p_text = utils.clean_text(p.get_text())
                if len(p_text.split()) > 15:
                    description = p_text
                    break
                    
        if not description:
            description = f"SHL assessment tool for evaluating candidate traits, cognitive abilities, and job fit."

        # 5. Extract Duration
        duration_elem = soup.find(id="test-duration")
        duration_raw = duration_elem.get_text() if duration_elem else None
        
        if not duration_raw:
            # Scan text for duration patterns
            duration_match = re.search(r"\b(\d+)\s*(?:min|minute|mins|minutes|hr|hour|hours|hrs)\b", body_text, re.I)
            if duration_match:
                duration_raw = duration_match.group(0)
            else:
                # Set default based on typical test type
                if "coding" in url.lower():
                    duration_raw = "45 minutes"
                elif "opq" in url.lower():
                    duration_raw = "30 minutes"
                else:
                    duration_raw = "30 minutes"

        duration = utils.normalize_duration(duration_raw)

        # 6. Extract Format / Assessment Type
        type_elem = soup.find(id="test-format")
        assessment_type = utils.clean_text(type_elem.get_text()) if type_elem else None
        
        if not assessment_type:
            name_lower = name.lower()
            if "coding" in name_lower or "simulation" in name_lower:
                assessment_type = "Coding Simulation"
            elif "questionnaire" in name_lower or "opq" in name_lower or "mq" in name_lower:
                assessment_type = "Questionnaire"
            elif "interactive" in name_lower:
                assessment_type = "Interactive"
            elif "judgement" in name_lower or "sjt" in name_lower:
                assessment_type = "Scenario-Based Simulation"
            else:
                assessment_type = "Multiple Choice"

        # 7. Extract Adaptive format
        adaptive_elem = soup.find(id="test-adaptive")
        adaptive_raw = utils.clean_text(adaptive_elem.get_text()) if adaptive_elem else None
        adaptive = self.clean_boolean(adaptive_raw)
        
        if adaptive is None:
            adaptive = "adaptive" in body_text.lower() or "cat" in body_text.lower().split()

        # 8. Extract Remote proctoring
        remote_elem = soup.find(id="test-remote")
        remote_raw = utils.clean_text(remote_elem.get_text()) if remote_elem else None
        remote_testing = self.clean_boolean(remote_raw)
        
        if remote_testing is None:
            # Most modern SHL tests are proctored/taken remotely online
            remote_testing = any(word in body_text.lower() for word in ["remote", "online", "anywhere", "unsupervised"]) or True

        # 9. Extract Test Level
        level_elem = soup.find(id="test-level")
        test_level = utils.clean_text(level_elem.get_text()) if level_elem else None
        
        if not test_level:
            levels = []
            body_text_lower = body_text.lower()
            for lvl in ["graduate", "manager", "entry-level", "professional", "executive", "operator"]:
                if lvl in body_text_lower:
                    levels.append(lvl.title())
            if levels:
                test_level = ", ".join(levels)
            else:
                test_level = "All Levels"

        # 10. Extract Lists: Skills, Competencies, Job Roles, Languages, Industry, Tags
        skills = self.extract_list_from_ul(soup.find(id="test-skills"))
        if not skills:
            # Keyword scanning fallback
            skills_db = [
                "numerical reasoning", "verbal reasoning", "deductive reasoning", "inductive reasoning", 
                "critical thinking", "coding", "software engineering", "behavioral style", 
                "situational judgment", "problem solving", "decision making", "calculation", 
                "verbal comprehension", "logical reasoning"
            ]
            body_text_lower = body_text.lower()
            for skill in skills_db:
                if skill in body_text_lower:
                    skills.append(skill.title())
            if not skills:
                skills = ["General Aptitude"]

        competencies = self.extract_list_from_ul(soup.find(id="test-competencies"))
        if not competencies:
            comp_db = [
                "analytical thinking", "decision making", "learning agility", "working with people", 
                "influence", "drive for results", "adaptability", "collaboration", "problem solving", 
                "communication", "teamwork", "leadership"
            ]
            body_text_lower = body_text.lower()
            for comp in comp_db:
                if comp in body_text_lower:
                    competencies.append(comp.title())
            if not competencies:
                competencies = ["Core Workplace Competencies"]

        job_roles = self.extract_list_from_ul(soup.find(id="test-job-roles"))
        if not job_roles:
            roles_db = [
                "software engineer", "backend developer", "frontend developer", "data analyst", 
                "consultant", "project manager", "sales representative", "hr manager", "team lead", 
                "executive", "financial analyst", "accountant", "customer service representative",
                "graduate trainee"
            ]
            body_text_lower = body_text.lower()
            for role in roles_db:
                if role in body_text_lower:
                    job_roles.append(role.title())
            if not job_roles:
                job_roles = ["All Professions"]

        languages = self.extract_list_from_ul(soup.find(id="test-languages"))
        if not languages:
            languages = ["English"] # default for the crawled English site

        industry = self.extract_list_from_ul(soup.find(id="test-industries"))
        if not industry:
            ind_db = [
                "technology", "finance", "healthcare", "consulting", "banking", "insurance", 
                "retail", "manufacturing", "e-commerce", "public sector", "legal"
            ]
            body_text_lower = body_text.lower()
            for ind in ind_db:
                if ind in body_text_lower:
                    industry.append(ind.title())
            if not industry:
                industry = ["All Industries"]

        tags = self.extract_list_from_ul(soup.find(id="test-tags"))
        if not tags:
            meta_keywords = soup.find("meta", attrs={"name": "keywords"})
            if meta_keywords:
                tags = utils.clean_list(meta_keywords.get("content", "").split(","))
            else:
                tags = [category] if category else []
                if "verify" in name.lower():
                    tags.append("Verify")
                if "opq" in name.lower():
                    tags.append("OPQ")

        # 11. Compile metadata
        metadata = {
            "crawled_url": url,
            "raw_duration_text": duration_raw.strip() if duration_raw else None,
            "raw_adaptive_text": "Yes" if adaptive else "No",
            "raw_remote_text": "Yes" if remote_testing else "No"
        }

        # 12. Create dictionary and validate with Pydantic
        assessment_dict = {
            "id": assessment_id,
            "name": name,
            "url": url,
            "category": category,
            "description": description,
            "assessment_type": assessment_type,
            "duration": duration,
            "skills": skills,
            "competencies": competencies,
            "job_roles": job_roles,
            "languages": languages,
            "remote_testing": remote_testing,
            "adaptive": adaptive,
            "test_level": test_level,
            "industry": industry,
            "tags": tags,
            "metadata": {k: v for k, v in metadata.items() if v is not None}
        }

        try:
            model = AssessmentModel(**assessment_dict)
            return model
        except ValidationError as e:
            logger.warning(
                f"Data quality validation failed for assessment from URL: {url}.\n"
                f"Errors: {e.errors()}\n"
                f"Extracted values: {json.dumps(assessment_dict, indent=2)}\n"
                f"Continuing execution without crash."
            )
            return None

    def parse_raw_file(self, raw_filepath: str, url: str) -> Optional[AssessmentModel]:
        """Reads a local raw HTML file, parses its contents, and saves individual processed JSON."""
        if not os.path.exists(raw_filepath):
            logger.error(f"Raw HTML file not found: {raw_filepath}")
            return None

        logger.info(f"Parsing raw HTML file: {raw_filepath}")
        with open(raw_filepath, "r", encoding="utf-8") as f:
            html_content = f.read()

        model = self.parse_html_content(html_content, url)
        
        if model:
            # Save individual processed output for debugging/transparency
            slug = os.path.splitext(os.path.basename(raw_filepath))[0]
            processed_filepath = os.path.join(config.PROCESSED_DIR, f"{slug}.json")
            
            with open(processed_filepath, "w", encoding="utf-8") as f:
                f.write(model.model_dump_json(indent=2))
                
            logger.info(f"Saved processed JSON to: {processed_filepath}")
            
        return model
