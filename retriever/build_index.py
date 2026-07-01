import argparse
import json
import os
import faiss
import numpy as np
from retriever import config, utils
from retriever.embedding_model import EmbeddingModel
from retriever.utils import logger


def compile_assessment_document(assessment: dict) -> str:
    """
    Combines key assessment fields into a single search document.
    Includes: Name, Description, Skills, Competencies, Job Roles, Type, Industry, Tags, Duration, and Language.
    """
    name = assessment.get("name", "")
    description = assessment.get("description", "")
    skills = ", ".join(assessment.get("skills", []))
    competencies = ", ".join(assessment.get("competencies", []))
    job_roles = ", ".join(assessment.get("job_roles", []))
    assessment_type = assessment.get("assessment_type", "")
    industry = ", ".join(assessment.get("industry", []))
    tags = ", ".join(assessment.get("tags", []))
    duration = assessment.get("duration", "")
    languages = ", ".join(assessment.get("languages", []))

    doc_parts = [
        f"Assessment Name: {name}",
        f"Description: {description}",
        f"Skills Measured: {skills}" if skills else "",
        f"Core Competencies: {competencies}" if competencies else "",
        f"Target Job Roles: {job_roles}" if job_roles else "",
        f"Assessment Type: {assessment_type}" if assessment_type else "",
        f"Target Industry: {industry}" if industry else "",
        f"Associated Tags: {tags}" if tags else "",
        f"Test Duration: {duration}" if duration else "",
        f"Languages: {languages}" if languages else ""
    ]
    
    # Filter out empty strings and join with double newlines for clear semantic segments
    return "\n".join([part for part in doc_parts if part])


def build_faiss_index(force_rebuild: bool = False) -> None:
    """
    Builds the FAISS vector index and saves metadata mapping.
    Skips generation if index and metadata files already exist, unless force_rebuild is True.
    """
    index_exists = os.path.exists(config.VECTOR_INDEX_PATH)
    meta_exists = os.path.exists(config.METADATA_PATH)

    if index_exists and meta_exists and not force_rebuild:
        logger.info("FAISS index and metadata already exist. Skipping index generation.")
        print("Completed (Index already built, skip rebuild)")
        return

    logger.info("Starting index build process...")

    # 1. Load assessments JSON
    if not os.path.exists(config.ASSESSMENTS_JSON_PATH):
        logger.error(f"Assessments database file not found: {config.ASSESSMENTS_JSON_PATH}")
        print("Error: assessments.json not found. Run scraper first.")
        return

    with open(config.ASSESSMENTS_JSON_PATH, "r", encoding="utf-8") as f:
        assessments = json.load(f)

    # 2. Inject Verify cognitive ability tests since they are grouped on the live site
    verify_tests = [
        {
            "id": "verify-g",
            "name": "SHL Verify G+ Test",
            "url": "https://www.shl.com/products/assessments/cognitive-assessments/",
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
            "url": "https://www.shl.com/products/assessments/cognitive-assessments/",
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
            "url": "https://www.shl.com/products/assessments/cognitive-assessments/",
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
            "url": "https://www.shl.com/products/assessments/cognitive-assessments/",
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

    # Append verify tests if not already present in loaded JSON
    existing_ids = {item.get("id") for item in assessments}
    for vt in verify_tests:
        if vt["id"] not in existing_ids:
            assessments.append(vt)

    logger.info(f"Loaded {len(assessments)} assessments (including cognitive verify expansions).")
    print("Loaded assessments")

    # 3. Compile documents and metadata mapping
    documents = []
    metadata_map = {}

    for idx, item in enumerate(assessments):
        doc = compile_assessment_document(item)
        documents.append(doc)
        
        # Save structural metadata separately mapping index to catalog item
        metadata_map[idx] = {
            "id": item.get("id"),
            "name": item.get("name"),
            "url": item.get("url"),
            "category": item.get("category"),
            "assessment_type": item.get("assessment_type"),
            "duration": item.get("duration"),
            "skills": item.get("skills", []),
            "competencies": item.get("competencies", []),
            "job_roles": item.get("job_roles", []),
            "languages": item.get("languages", []),
            "industry": item.get("industry", []),
            "tags": item.get("tags", []),
            "description": item.get("description", "")
        }

    # 4. Load Embedding model and generate embeddings
    print("Generating embeddings")
    model = EmbeddingModel()
    logger.info("Generating embeddings for documents...")
    embeddings = model.get_embeddings(documents)

    # 5. Build FAISS Index
    print("Saving FAISS")
    dimension = config.EMBEDDING_DIMENSION
    
    # We use IndexFlatIP (Inner Product) to compute cosine similarity on L2-normalized embeddings
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    # Write vectors to index
    faiss.write_index(index, config.VECTOR_INDEX_PATH)
    logger.info(f"FAISS index written to: {config.VECTOR_INDEX_PATH}. Size: {index.ntotal}")

    # Write metadata map
    utils.save_metadata(metadata_map, config.METADATA_PATH)

    # Write logs
    logger.info(
        f"Retrieval build complete. Model: {config.EMBEDDING_MODEL}, "
        f"Dimensions: {dimension}, Document count: {len(documents)}, "
        f"Index size: {os.path.getsize(config.VECTOR_INDEX_PATH)} bytes."
    )

    print("Completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build/rebuild the Semantic Retrieval vector store.")
    parser.add_argument(
        "--rebuild", 
        action="store_true", 
        help="Force rebuild of the FAISS index even if it already exists"
    )
    args = parser.parse_args()

    build_faiss_index(force_rebuild=args.rebuild)
