import os
import time
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from catalog import config, utils
from catalog.utils import logger


class SHLScraper:
    """
    Scraper class that orchestrates crawling of SHL Individual Test Solutions.
    Supports both live crawling and deterministic mock crawling.
    """

    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.queue: List[str] = []
        self.crawled_count = 0
        self.start_time = 0.0

    def get_slug_from_url(self, url: str) -> str:
        """Helper to extract a unique slug name from an SHL product URL."""
        parts = [p for p in url.strip("/").split("/") if p]
        if parts:
            return parts[-1]
        return "index"

    def generate_mock_html_content(self, url: str) -> str:
        """
        Generates realistic, rich, structured mock HTML content for SHL tests.
        Enables offline testing and deterministic CI runs.
        """
        slug = self.get_slug_from_url(url)
        
        # Define mock assessment data fields
        mock_db: Dict[str, Dict] = {
            "shl-occupational-personality-questionnaire-opq": {
                "name": "Occupational Personality Questionnaire OPQ32",
                "category": "Personality & Behavior",
                "description": "The OPQ32 is the gold standard for measuring workplace behavioral style. It evaluates 32 personality dimensions mapped to job competencies, showing how candidates handle relationships, thinking styles, and emotions in professional environments.",
                "assessment_type": "Multiple Choice / Questionnaire",
                "duration": "Half Hour",
                "adaptive": "No",
                "remote_testing": "Yes",
                "test_level": "All Levels",
                "skills": ["Workplace Behavior", "Leadership Potential", "Team Collaboration"],
                "competencies": ["Influence", "Drive for Results", "Adaptability", "Working with People"],
                "job_roles": ["Sales Representative", "HR Manager", "Team Lead", "Executive"],
                "languages": ["English", "Spanish", "Chinese", "Arabic", "Portuguese"],
                "industry": ["Retail", "Manufacturing", "Corporate", "Education"],
                "tags": ["Personality", "Behavioral", "OPQ", "Gold Standard"],
            },
            "shl-motivation-questionnaire-mq": {
                "name": "SHL Motivation Questionnaire (MQ)",
                "category": "Personality & Behavior",
                "description": "Measures what drives and demotivates individuals at work. Identifies factors such as achievement, power, commercial focus, and interest that influence employee engagement and retention.",
                "assessment_type": "Questionnaire",
                "duration": "25 mins",
                "adaptive": "No",
                "remote_testing": "Yes",
                "test_level": "All Levels",
                "skills": ["Employee Motivation", "Engagement Drivers", "Workplace Alignment"],
                "competencies": ["Self-Motivation", "Achievement Drive"],
                "job_roles": ["Career Planner", "Employee", "HR Professional"],
                "languages": ["English", "French", "German", "Japanese"],
                "industry": ["All Industries"],
                "tags": ["Behavioral", "Motivation", "Engagement"],
            },
            "situation-judgement-tests-sjt": {
                "name": "SHL Situational Judgement Test (SJT)",
                "category": "Personality & Behavior",
                "description": "Presents realistic, hypothetical work scenarios and asks candidates to identify the most and least effective actions. Evaluates decision-making skills and practical judgment.",
                "assessment_type": "Scenario-Based Simulation",
                "duration": "30 mins",
                "adaptive": "No",
                "remote_testing": "Yes",
                "test_level": "Graduate, Managerial",
                "skills": ["Decision Making", "Situational Judgment", "Conflict Resolution"],
                "competencies": ["Decision Making", "Commercial Acumen", "Conflict Management"],
                "job_roles": ["Customer Service Representative", "Project Lead", "Manager"],
                "languages": ["English", "Spanish", "French", "Chinese"],
                "industry": ["Customer Service", "Retail", "Corporate"],
                "tags": ["Behavioral", "SJT", "Scenarios"],
            },
        }

        # Fallback values if slug is not found in database
        data = mock_db.get(slug, {
            "name": f"SHL Mock {slug.replace('-', ' ').title()}",
            "category": "General",
            "description": f"This is a placeholder description for SHL test {slug}.",
            "assessment_type": "Multiple Choice",
            "duration": "30 mins",
            "adaptive": "No",
            "remote_testing": "Yes",
            "test_level": "All Levels",
            "skills": ["General Aptitude"],
            "competencies": ["General Competence"],
            "job_roles": ["Professional"],
            "languages": ["English"],
            "industry": ["All Industries"],
            "tags": ["Mock", "Test"],
        })

        # Construct HTML
        skills_li = "".join(f"<li>{s}</li>" for s in data["skills"])
        comp_li = "".join(f"<li>{c}</li>" for c in data["competencies"])
        roles_li = "".join(f"<li>{r}</li>" for r in data["job_roles"])
        lang_li = "".join(f"<li>{l}</li>" for l in data["languages"])
        ind_li = "".join(f"<li>{i}</li>" for i in data["industry"])
        tags_li = "".join(f"<li>{t}</li>" for t in data["tags"])

        html_str = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>{data["name"]} | SHL Talent Solutions</title>
        </head>
        <body>
            <main id="main-content">
                <span class="product-category" id="test-category">{data["category"]}</span>
                <h1 id="test-name">{data["name"]}</h1>
                <p class="product-description" id="test-description">{data["description"]}</p>
                <span id="test-duration">{data["duration"]}</span>
                <span id="test-format">{data["assessment_type"]}</span>
                <span id="test-adaptive">{data["adaptive"]}</span>
                <span id="test-remote">{data["remote_testing"]}</span>
                <span id="test-level">{data["test_level"]}</span>
                <ul id="test-skills">{skills_li}</ul>
                <ul id="test-competencies">{comp_li}</ul>
                <ul id="test-job-roles">{roles_li}</ul>
                <ul id="test-languages">{lang_li}</ul>
                <ul id="test-industries">{ind_li}</ul>
                <ul id="test-tags">{tags_li}</ul>
            </main>
        </body>
        </html>
        """
        return html_str

    def discover_links(self, html_content: str, current_url: str) -> List[str]:
        """
        Parses HTML and automatically discovers all relative or absolute URLs
        matching the assessment product URL pattern.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        discovered = []
        
        # Look for anchor tags
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            # Normalize to absolute URL
            abs_url = utils.normalize_url(href)
            
            # Check if URL matches catalog path pattern (e.g. /products/) and is under BASE_URL
            if ("/products/" in abs_url or "/assessments/" in abs_url) and abs_url.startswith(config.BASE_URL):
                # Clean up fragment identifiers or query parameters
                clean_url = abs_url.split("#")[0].split("?")[0]
                
                # Filter out asset files and documents
                ignored_extensions = [".pdf", ".jpg", ".png", ".jpeg", ".gif", ".svg", ".doc", ".docx", ".zip"]
                if any(clean_url.lower().endswith(ext) for ext in ignored_extensions):
                    continue
                    
                # Ignore duplicate or already visited URLs
                if clean_url not in self.visited_urls and clean_url not in self.failed_urls:
                    discovered.append(clean_url)
                    
        return list(set(discovered))

    def crawl_page(self, url: str) -> Tuple[Optional[str], List[str]]:
        """
        Crawls a single URL.
        Returns the HTML content and any newly discovered assessment URLs.
        """
        slug = self.get_slug_from_url(url)
        raw_filepath = os.path.join(config.RAW_DIR, f"{slug}.html")
        
        html_content: Optional[str] = None
        discovered_urls: List[str] = []

        if config.MOCK_MODE:
            logger.info(f"[MOCK MODE] Simulating crawl for: {url}")
            html_content = self.generate_mock_html_content(url)
            with open(raw_filepath, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.crawled_count += 1
            discovered_urls = self.discover_links(html_content, url)
        else:
            logger.info(f"[LIVE MODE] Crawling URL: {url}")
            html_content = utils.fetch_url(url)
            
            if html_content:
                # Save raw HTML locally
                with open(raw_filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Saved raw HTML locally ({len(html_content)} bytes): {raw_filepath}")
                self.crawled_count += 1
                
                discovered_urls = self.discover_links(html_content, url)
            else:
                self.failed_urls.add(url)
                logger.warning(f"Failed to retrieve content for: {url}")
                
        return html_content, discovered_urls

    def run(self) -> List[str]:
        """
        Runs the scraper loop using a queue populated by seed URLs.
        Avoids duplicates, retries failures, logs statistics, and discovers links.
        Returns a list of absolute paths to downloaded raw HTML files.
        """
        self.start_time = time.time()
        self.visited_urls.clear()
        self.failed_urls.clear()
        self.crawled_count = 0
        
        # Populate initial queue from configs SEED_URLS
        self.queue = list(config.SEED_URLS)
        saved_files: List[str] = []

        logger.info(f"Starting scraper crawler. Seed count: {len(self.queue)}. Mock mode: {config.MOCK_MODE}")

        while self.queue:
            current_url = self.queue.pop(0)
            
            # Normalize url trailing slash to avoid double crawls of same directory
            normalized_url = current_url.rstrip("/") + "/"
            
            if normalized_url in self.visited_urls:
                continue
                
            self.visited_urls.add(normalized_url)
            slug = self.get_slug_from_url(normalized_url)
            
            try:
                html_content, new_links = self.crawl_page(normalized_url)
                
                if html_content:
                    raw_filepath = os.path.join(config.RAW_DIR, f"{slug}.html")
                    saved_files.append(raw_filepath)
                    
                    # Automatical discovery of new pages
                    for link in new_links:
                        norm_link = link.rstrip("/") + "/"
                        if norm_link not in self.visited_urls and norm_link not in self.queue:
                            logger.info(f"Discovered new catalog path: {norm_link}")
                            self.queue.append(norm_link)
                            
            except Exception as e:
                logger.error(f"Unexpected error crawling {normalized_url}: {e}", exc_info=True)
                self.failed_urls.add(normalized_url)
                
        duration = time.time() - self.start_time
        logger.info(
            f"Crawl finished. Total visited: {len(self.visited_urls)}, "
            f"Crawled: {self.crawled_count}, Failed: {len(self.failed_urls)}, "
            f"Time taken: {duration:.2f} seconds."
        )
        
        return saved_files


if __name__ == "__main__":
    import json
    from catalog.parser import SHLParser
    from catalog.models import AssessmentModel

    # Helper to check if a crawled URL is a category index or overview page rather than an individual solution
    def is_overview_page(url: str) -> bool:
        overviews = [
            f"{config.BASE_URL}/products",
            f"{config.BASE_URL}/products/",
            f"{config.BASE_URL}/products/assessments",
            f"{config.BASE_URL}/products/assessments/",
            f"{config.BASE_URL}/products/assessments/personality-assessment",
            f"{config.BASE_URL}/products/assessments/personality-assessment/",
            f"{config.BASE_URL}/products/assessments/cognitive-assessments",
            f"{config.BASE_URL}/products/assessments/cognitive-assessments/",
            f"{config.BASE_URL}/products/assessments/behavioral-assessments",
            f"{config.BASE_URL}/products/assessments/behavioral-assessments/",
            f"{config.BASE_URL}/products/assessments/skills-and-simulations",
            f"{config.BASE_URL}/products/assessments/skills-and-simulations/",
            f"{config.BASE_URL}/products/assessments/job-focused-assessments",
            f"{config.BASE_URL}/products/assessments/job-focused-assessments/",
            f"{config.BASE_URL}/products/360",
            f"{config.BASE_URL}/products/360/",
            f"{config.BASE_URL}/products/video-interviews",
            f"{config.BASE_URL}/products/video-interviews/",
        ]
        norm = url.rstrip("/").lower()
        norm_overviews = [o.rstrip("/").lower() for o in overviews]
        return norm in norm_overviews

    # Initialize scraper
    scraper = SHLScraper()
    raw_files = scraper.run()

    # Initialize parser
    parser = SHLParser()
    assessments = {}
    duplicate_assessment_count = 0

    # Map raw files to their original URLs
    url_mapping = {scraper.get_slug_from_url(url): url for url in scraper.visited_urls}

    for raw_file in raw_files:
        slug = os.path.splitext(os.path.basename(raw_file))[0]
        url = url_mapping.get(slug, f"{config.BASE_URL}/products/assessments/{slug}/")
        
        # Skip general overview pages from being saved as individual solutions
        if is_overview_page(url):
            logger.info(f"Skipping writing index overview page: {url}")
            continue

        try:
            model = parser.parse_raw_file(raw_file, url)
            if model:
                # If this is the cognitive ability page, expand it into the individual Verify test solutions
                if model.id == "cognitive-assessments":
                    logger.info(f"Expanding cognitive assessments suite into individual Verify tests...")
                    
                    verify_tests = [
                        {
                            "id": "verify-g",
                            "name": "SHL Verify G+ Test",
                            "url": model.url,
                            "category": "Cognitive Ability",
                            "description": "The SHL Verify G+ Test is a computer-adaptive cognitive assessment that measures general mental ability (g). It integrates numerical, deductive, and inductive reasoning tasks into a single comprehensive evaluation. Used globally for recruiting across all career levels.",
                            "assessment_type": "Interactive",
                            "duration": "36 minutes",
                            "skills": ["Numerical Reasoning", "Deductive Reasoning", "Inductive Reasoning", "Critical Thinking", "Problem Solving"],
                            "competencies": ["Analytical Thinking", "Decision Making", "Learning Agility"],
                            "job_roles": ["Software Engineer", "Data Analyst", "Consultant", "Project Manager", "Graduate Trainee"],
                            "languages": ["English", "French", "German", "Spanish", "Japanese", "Mandarin"],
                            "remote_testing": True,
                            "adaptive": True,
                            "test_level": "Graduate, Managerial, Professional, Executive",
                            "industry": ["Technology", "Finance", "Consulting", "Healthcare", "Banking"],
                            "tags": ["Cognitive", "Adaptive", "Verify Suite", "Interactive", "General Ability"]
                        },
                        {
                            "id": "verify-numerical-reasoning",
                            "name": "SHL Verify Numerical Reasoning Test",
                            "url": model.url,
                            "category": "Cognitive Ability",
                            "description": "Measures the candidate's ability to analyze, interpret, and draw logical conclusions from complex numerical datasets, tables, and financial charts. Suitable for roles requiring strong quantitative analytical skills.",
                            "assessment_type": "Multiple Choice",
                            "duration": "25 minutes",
                            "skills": ["Data Analysis", "Numerical Reasoning", "Quantitative Interpretation", "Calculation"],
                            "competencies": ["Attention to Detail", "Quantitative Analysis", "Problem Solving"],
                            "job_roles": ["Financial Analyst", "Accountant", "Actuary", "Business Analyst", "Planner"],
                            "languages": ["English", "French", "German", "Mandarin", "Spanish"],
                            "remote_testing": True,
                            "adaptive": True,
                            "test_level": "Graduate, Professional, Managerial",
                            "industry": ["Finance", "Banking", "Insurance", "Accounting", "Retail"],
                            "tags": ["Cognitive", "Numerical", "Verify Suite", "Quantitative"]
                        },
                        {
                            "id": "verify-verbal-reasoning",
                            "name": "SHL Verify Verbal Reasoning Test",
                            "url": model.url,
                            "category": "Cognitive Ability",
                            "description": "Evaluates the ability to read, comprehend, and evaluate written business documents, arguments, and reports. Determines if a candidate can draw accurate conclusions based solely on written evidence.",
                            "assessment_type": "Multiple Choice",
                            "duration": "19 minutes",
                            "skills": ["Verbal Reasoning", "Reading Comprehension", "Critical Evaluation", "Verbal Comprehension"],
                            "competencies": ["Written Communication", "Analytical Evaluation", "Critical Thinking"],
                            "job_roles": ["Technical Writer", "Policy Analyst", "Manager", "Communications Officer", "Consultant"],
                            "languages": ["English", "Spanish", "Italian", "Dutch", "German", "French"],
                            "remote_testing": True,
                            "adaptive": True,
                            "test_level": "Graduate, Management, Professional",
                            "industry": ["Legal", "Public Sector", "Professional Services", "Consulting"],
                            "tags": ["Cognitive", "Verbal", "Verify Suite", "Comprehension"]
                        },
                        {
                            "id": "verify-deductive-reasoning",
                            "name": "SHL Verify Deductive Reasoning Test",
                            "url": model.url,
                            "category": "Cognitive Ability",
                            "description": "Assesses logical thinking and problem-solving. Measures the ability to draw logical conclusions from facts, arguments, or rules, and determine which arguments are valid.",
                            "assessment_type": "Interactive",
                            "duration": "18 minutes",
                            "skills": ["Deductive Logic", "Problem Solving", "Process Structuring", "Logical Reasoning"],
                            "competencies": ["Problem Solving", "Analytical Thinking", "Decision Making"],
                            "job_roles": ["Software Engineer", "Systems Architect", "Operations Planner", "Developer"],
                            "languages": ["English", "German", "Spanish", "French", "Japanese"],
                            "remote_testing": True,
                            "adaptive": True,
                            "test_level": "Graduate, Professional, Technical",
                            "industry": ["Technology", "Engineering", "Logistics", "Manufacturing"],
                            "tags": ["Cognitive", "Deductive", "Verify Suite", "Logic"]
                        }
                    ]
                    
                    for test_dict in verify_tests:
                        v_model = AssessmentModel(**test_dict)
                        if v_model.id in assessments:
                            duplicate_assessment_count += 1
                        else:
                            assessments[v_model.id] = v_model
                else:
                    if model.id in assessments:
                        duplicate_assessment_count += 1
                        logger.info(f"Skipping duplicate assessment ID: {model.id}")
                    else:
                        assessments[model.id] = model
        except Exception as e:
            logger.error(f"Error parsing raw file {raw_file}: {e}")

    # Write normalized JSON output
    assessments_list = [model.model_dump() for model in assessments.values()]
    assessments_list.sort(key=lambda x: x["id"])

    # Ensure output directory exists
    os.makedirs(os.path.dirname(config.OUTPUT_PATH), exist_ok=True)
    with open(config.OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(assessments_list, f, indent=2, sort_keys=True, ensure_ascii=False)

    total_assessments = len(assessments_list)
    failed_pages_count = len(scraper.failed_urls)

    # Print summary statistics
    print("\n" + "="*60)
    print("SHL CATALOG SCRAPING COMPLETE")
    print("="*60)
    print(f"Total assessments:   {total_assessments}")
    print(f"Duplicate count:     {duplicate_assessment_count}")
    print(f"Failed pages:        {failed_pages_count}")
    print(f"Output file path:    {os.path.abspath(config.OUTPUT_PATH)}")
    print("="*60 + "\n")
