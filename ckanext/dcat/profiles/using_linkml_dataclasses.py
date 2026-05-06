#!/usr/bin/env python3
"""
NFDI4Chem to DCAT-AP+ / ChemDCAT-AP RDF Converter

This script processes chemical dataset metadata from the NFDI4Chem Search Service API
and converts it into RDF graphs compliant with the DCAT-AP+ and/or
ChemDCAT-AP schemas using LinkML.

Features:
    - Fetches dataset lists or individual records from the CKAN-based API.
    - Resolves chemical identifiers (InChIKey, SMILES) to PubChem CIDs.
    - Transforms JSON metadata into LinkML dataclasses.
    - Serializes data to RDF/Turtle format.
    - Supports batch processing with error logging and retry tracking.

Usage Examples:
    # Process default test datasets, saving files to ./output/
    python using_linkml_dataclasses.py

    # Process specific IDs from a file, using both schemas
    python using_linkml_dataclasses.py -f dataset_ids.txt

    # Use a local schema folder (required for ChemDCAT-AP until PURL is live)
    python using_linkml_dataclasses.py -f ids.txt --local-schema-dir ./schemas

    # Debug mode: Print RDF to console instead of saving files
    python using_linkml_dataclasses.py -f ids.txt -of stdout --log-level INFO

Dependencies:
    - requests
    - linkml-runtime
    - rdflib
    - dcat-ap-plus (custom package)
    - chem-dcat-ap (custom package)

Date: 2026
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from linkml_runtime.dumpers import RDFLibDumper
from linkml_runtime.utils.schemaview import SchemaView
from rdflib import Graph

# --- DCAT-AP+ Imports ---
from dcat_ap_plus.datamodel.dcat_ap_plus import (
    Agent, Dataset, DataGeneratingActivity, DefinedTerm, Document,
    EvaluatedEntity, Entity, Concept, Identifier, LegalResource,
    Standard, QualitativeAttribute, QuantitativeAttribute, LinguisticSystem
)

# --- ChemDCAT-AP Imports ---
from chem_dcat_ap.datamodel.chem_dcat_ap import (
    SubstanceSample, SubstanceSampleCharacterizationDataset,
    SubstanceSampleCharacterization, InChi, InChIKey, IUPACName,
    SMILES, MolecularFormula, MolarMass, ChemicalEntity
)

# --- Constants ---
DEFAULT_IDS: List[str] = [
    "10-22000-1105",
    "10-14272-ymlgbyytihvwrb-yadaresesa-n-chmo0000593"
]
API_BASE_URL: str = "https://search.nfdi4chem.de/api/3/action/"
SCHEMA_URL_DCAT_AP_PLUS: str = "https://w3id.org/nfdi-de/dcat-ap-plus/"
SCHEMA_URL_CHEM_DCAT_AP: str = None # "https://w3id.org/nfdi-de/dcat-ap-plus/chemistry" # uncomment once PURL is live
REQUEST_TIMEOUT: int = 15


class OutputFormat(str, Enum):
    """Enumeration of supported output destinations."""
    FILE = "file"
    STDOUT = "stdout"


class ShapeType(str, Enum):
    """Enumeration of supported RDF schema shapes."""
    DCAT_AP_PLUS = "dcat-ap-plus"
    CHEM_DCAT_AP = "chem-dcat-ap"

class LogLevel(str, Enum):
    """Enumeration of valid logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class Config:
    """
    Runtime configuration container.

    Attributes:
        input_file: Path to a text file containing dataset IDs.
        shapes: List of schema shapes to generate.
        output_format: Destination for the RDF output (file or stdout).
        log_level: Logging verbosity level.
        local_schema_dir: Optional path to local schema YAML files.
        output_dir: Root directory for saving output files.
    """
    input_file: Optional[Path]
    shapes: List[ShapeType]
    output_format: OutputFormat
    log_level: LogLevel
    local_schema_dir: Optional[Path] = None
    output_dir: Path = field(default=Path("output"))


@dataclass
class ProcessingResult:
    """
    Statistics tracker for the batch processing job.

    Attributes:
        total: Total number of datasets attempted.
        successful: Number of datasets processed successfully for all shapes.
        failed_all: Number of datasets that failed for all requested shapes.
        failed_partial: Number of datasets where only some shapes succeeded.
        skipped_ids: List of IDs that failed completely.
    """
    total: int = 0
    successful: int = 0
    failed_all: int = 0
    failed_partial: int = 0
    skipped_ids: List[str] = field(default_factory=list)


# --- Logging Setup ---

def setup_logging(level: LogLevel) -> logging.Logger:
    """
    Configures the root logger with console and file handlers.

    Args:
        level: The logging level enum (e.g., LogLevel.INFO).

    Returns:
        The configured logger instance.
    """
    # Convert Enum member to its integer value (e.g., LogLevel.INFO -> 20)
    numeric_level = level.value

    if not logging.getLogger().hasHandlers():
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("skipped_datasets.log", mode='a')
            ]
        )

    logging.getLogger("linkml_runtime").setLevel(logging.WARNING)
    logging.getLogger("linkml").setLevel(logging.WARNING)

    return logging.getLogger(__name__)


# --- Data Access Layer ---

def fetch_json(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[Dict[str, Any]]:
    """
    Performs a generic HTTP GET request and parses the JSON response.

    Args:
        url: The target URL.
        timeout: Request timeout in seconds.

    Returns:
        A dictionary of the JSON response, or None if the request fails.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.debug(f"Request failed for {url}: {e}")
        return None
    except ValueError as e:
        logger.debug(f"JSON decode failed for {url}: {e}")
        return None


def fetch_dataset_ids(api_url: str = f"{API_BASE_URL}package_list") -> List[str]:
    """
    Fetches the complete list of dataset IDs from the NFDI4Chem Search Service API.

    Args:
        api_url: The API endpoint for listing packages.

    Returns:
        A list of dataset ID strings.

    Raises:
        ValueError: If the API response structure is invalid.
    """
    data = fetch_json(api_url, timeout=15)
    if not data or 'result' not in data:
        raise ValueError("API response missing 'result' key")

    result_data = data['result']
    if not isinstance(result_data, list):
        raise ValueError(f"Expected 'result' to be a list, got {type(result_data)}")

    logger.info(f"Fetched {len(result_data)} dataset IDs from {api_url}")
    return [str(x) for x in result_data]


def fetch_dataset(dataset_id: str, api_url: str = f"{API_BASE_URL}package_show?id=") -> Optional[Dict[str, Any]]:
    """
    Fetches metadata for a single dataset by its ID.

    Args:
        dataset_id: The unique identifier of the dataset.
        api_url: The base URL for the package show endpoint.

    Returns:
        A dictionary containing the dataset metadata, or None if fetch fails.
    """
    url = f"{api_url}{dataset_id}"
    data = fetch_json(url, timeout=10)

    if data and 'result' in data:
        return data['result']

    if data:
        logger.warning(f"Response for '{dataset_id}' missing 'result' key. Returning root.")
        return data

    return None


def load_ids_from_file(file_path: Path) -> List[str]:
    """
    Loads dataset IDs from a local text file.

    Supports two formats:
    1. JSON list: ["id1", "id2"]
    2. Newline-separated: id1\\nid2

    Args:
        file_path: Path to the input file.

    Returns:
        A list of dataset ID strings.

    Raises:
        FileNotFoundError: If the input file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    content = file_path.read_text(encoding='utf-8').strip()
    if not content:
        return []

    # Try parsing as JSON first
    try:
        data = json.loads(content)
        if isinstance(data, list):
            logger.info(f"Loaded {len(data)} IDs from JSON list in {file_path}")
            return [str(x) for x in data]
    except json.JSONDecodeError:
        pass

    # Fallback to newline-separated list
    ids = [line.strip() for line in content.splitlines() if line.strip()]
    logger.info(f"Loaded {len(ids)} IDs from newline-separated list in {file_path}")
    return ids


# --- Schema Management ---

def load_schema_view(shape: ShapeType, local_dir: Optional[Path] = None) -> SchemaView:
    """
    Loads a SchemaView with a robust fallback strategy:
    1. Attempt to load from public PURL (Remote).
    2. If remote fails, attempt to load from local 'schemas/' folder (Sibling to script).
    3. If local fails, attempt to load from user-provided '--local-schema-dir'.
    4. If all fail, raise a descriptive FileNotFoundError.

    Args:
        shape: The type of schema to load (DCAT-AP+ or ChemDCAT-AP).
        local_dir: Optional path provided via --local-schema-dir.

    Returns:
        A configured SchemaView instance.

    Raises:
        FileNotFoundError: If the schema cannot be found remotely or locally.
    """
    # Define identifiers
    if shape == ShapeType.DCAT_AP_PLUS:
        purl = SCHEMA_URL_DCAT_AP_PLUS
        local_filename = "dcat_ap_plus.yaml"
    elif shape == ShapeType.CHEM_DCAT_AP:
        # Note: We don't have a working PURL for Chem yet, but we try a placeholder or skip remote if known broken.
        # To strictly follow your request "try PURL first", we attempt the URL.
        # If you know the Chem PURL, put it here. If not, we can force local first for Chem.
        # Assuming you want to try a PURL if it existed, but since Chem PURL is broken,
        # let's make an exception: If we KNOW the PURL is dead, we skip step 1 for Chem to save time.

        # STRATEGY A: Try PURL for both (as requested).
        # If Chem PURL is totally dead (404/timeout), this will delay startup.
        # STRATEGY B (Recommended): Skip remote for Chem if we know it's dead.

        # Let's implement your request: Try PURL first.
        # For Chem, we'll use a dummy or the future PURL if known.
        # If you don't have a Chem PURL yet, set this to None to skip step 1 for Chem.
        purl = SCHEMA_URL_CHEM_DCAT_AP
        local_filename = "chem_dcat_ap.yaml"
    else:
        raise ValueError(f"Unknown shape: {shape}")

    # --- Step 1: Try Remote PURL ---
    if purl:
        try:
            logger.debug(f"Attempting to load {shape.value} from remote PURL: {purl}")
            # We use a short timeout to fail fast if the PURL is dead
            return SchemaView(purl, merge_imports=True)
        except Exception as e:
            logger.info(f"Remote load failed for {shape.value} ({e}). Falling back to local files...")

    # --- Step 2: Try Local Sibling Folder ---
    # Assumes script is in '.../profiles/' and schemas are in '.../schemas/'
    script_dir = Path(__file__).parent
    sibling_schemas_dir = script_dir.parent / "schemas"
    local_path = sibling_schemas_dir / local_filename

    if local_path.exists():
        logger.debug(f"Loaded {shape.value} from local sibling folder: {local_path}")
        return SchemaView(str(local_path), merge_imports=True)

    # --- Step 3: Try User-Provided Directory ---
    if local_dir:
        manual_path = local_dir / local_filename
        if manual_path.exists():
            logger.debug(f"Loaded {shape.value} from user-provided dir: {manual_path}")
            return SchemaView(str(manual_path), merge_imports=True)

    # --- Step 4: All Failed ---
    raise FileNotFoundError(
        f"Failed to load schema '{shape.value}'.\n"
        f"1. Remote PURL failed or was skipped.\n"
        f"2. Local file not found at: {local_path}\n"
        f"3. User-provided dir ({local_dir}) did not contain '{local_filename}'.\n\n"
        f"Solution: Ensure '{local_filename}' exists in the 'schemas' folder sibling to this script, "
        f"or provide the correct path using --local-schema-dir /path/to/schemas"
    )


# --- Domain Logic (Transformation) ---

class PubChemCache:
    """
    Simple in-memory cache for PubChem CID lookups to avoid redundant API calls.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, Optional[str]] = {}

    def get_cid(self, inchi_key: Optional[str] = None, smiles: Optional[str] = None) -> Optional[str]:
        """
        Retrieves the PubChem CID for a given InChIKey or SMILES string.

        Args:
            inchi_key: The InChIKey identifier (case-insensitive).
            smiles: The SMILES string representation.

        Returns:
            The CID string if found, otherwise None.
        """
        # Normalize key
        key = (inchi_key.strip().upper() if inchi_key else None) or \
              (smiles.strip() if smiles else None)

        if not key:
            return None
        if key in self._cache:
            return self._cache[key]

        try:
            suffix = f"inchikey/{key}" if inchi_key else f"smiles/{smiles}"
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{suffix}/cids/TXT"
            resp = requests.get(url, headers={"Accept": "text/plain"}, timeout=10)

            if resp.status_code == 200 and resp.text.strip():
                cid = resp.text.strip().split("\n")[0]
                if cid.isdigit():
                    self._cache[key] = cid
                    return cid

            self._cache[key] = None
        except Exception:
            self._cache[key] = None

        return None


# Global cache instance
_pubchem = PubChemCache()


def _build_compound_id(dataset_id: str, data: Dict[str, Any]) -> str:
    """
    Constructs the URI for the chemical compound.

    Attempts to resolve a PubChem CID; if successful, returns the PubChem URI.
    Otherwise, returns a local fragment URI based on the dataset ID.

    Args:
        dataset_id: The base dataset URI.
        data: The dataset metadata dictionary.

    Returns:
        The resolved compound URI string.
    """
    default_id = f"{dataset_id}#sample_compound"
    inchi_key = data.get("inchi_key")
    smiles = data.get("smiles")

    if cid := _pubchem.get_cid(inchi_key, smiles):
        return f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
    return default_id


def _get_description(dataset_dict: Dict[str, Any]) -> str:
    """Extracts and cleans the dataset description."""
    desc = dataset_dict.get('notes')
    return desc.strip() if desc else 'No description'


def _get_authors(dataset_dict: Dict[str, Any]) -> List[Agent]:
    """
    Parses the author string into a list of Agent objects.

    Handles various formats: "Last, First", "Last, Initial", or lists of names.

    Args:
        dataset_dict: The dataset metadata dictionary.

    Returns:
        A list of Agent objects representing the creators.
    """
    creators: List[Agent] = []
    author_string = dataset_dict.get("author")

    if not author_string or not isinstance(author_string, str):
        return creators

    fragments = [f.strip() for f in author_string.split(",") if f.strip()]
    if not fragments:
        return creators

    full_names: List[str] = []

    # Heuristic: Check for single "Last, First" format
    is_single_author = (
            len(fragments) == 2 and
            len(fragments[1]) > 2 and
            fragments[1].replace(".", "").isalpha() and
            " " not in fragments[0]
    )

    if is_single_author:
        full_names.append(f"{fragments[0]} {fragments[1]}")
    else:
        for fragment in fragments:
            clean_frag = fragment.strip()
            if not clean_frag:
                continue

            is_likely_initial = len(clean_frag) <= 2 and clean_frag.replace(".", "").isalpha()

            if is_likely_initial and full_names:
                last_name = full_names.pop()
                full_names.append(f"{last_name} {clean_frag}")
            else:
                full_names.append(clean_frag)

    for name in full_names:
        if name.endswith("."):
            parts = name.split()
            if parts and len(parts[-1]) > 3:
                name = name[:-1]

        name = " ".join(name.split())
        if name:
            creators.append(Agent(
                name=name,
                type=Concept(preferred_label='person', description='A human being.')
            ))

    return creators


def _get_publisher(dataset_dict: Dict[str, Any]) -> Agent:
    """Extracts organization info and creates a Publisher Agent."""
    org = dataset_dict.get("organization") or {}
    org_name = org.get("title") or org.get("display_name") or org.get("name") or "Unknown Organization"

    return Agent(
        name=org_name,
        type=Concept(
            preferred_label='Academia/Scientific organisation',
            description='http://purl.org/adms/publishertype/Academia-ScientificOrganisation'
        )
    )


def _get_license(dataset_dict: Dict[str, Any], dataset_id: str) -> List[LegalResource]:
    """Extracts license information and creates a LegalResource object."""
    if not dataset_dict.get('license_title'):
        return []

    title = dataset_dict['license_title']
    license_id = dataset_dict.get('license_id')
    license_url = dataset_dict.get('license_url')

    if license_id != 'notspecified' and license_url:
        url = license_url
    else:
        url = f"{dataset_id}#license_notspecified"

    return [LegalResource(id=url, title=title)]


def _get_language(dataset_dict: Dict[str, Any]) -> LinguisticSystem:
    """Determines the dataset language and returns a LinguisticSystem object."""
    raw = (dataset_dict.get('language') or 'en').strip().lower()
    code = 'de' if raw in ('deutsch', 'german', 'de') else 'en'
    return LinguisticSystem(title=code, description=f"http://id.loc.gov/vocabulary/iso639-1/{code}")


def _get_url(dataset_dict: Dict[str, Any]) -> List[Document]:
    """Extracts the landing page URL if valid."""
    url = dataset_dict.get('url')
    if url and "https://" in str(url):
        return [Document(id=url)]
    return []


def _build_dcat_graph(
        data: Dict[str, Any],
        ds_id: str,
        cmp_id: str,
        samp_id: str,
        meas_id: str,
        schema_view: SchemaView,
        prefix_map: Dict[str, str]
) -> Graph:
    """Constructs the RDF Graph using DCAT-AP+ classes."""
    compound_obj = Entity(
        id=cmp_id,
        rdf_type=DefinedTerm(id='http://purl.obolibrary.org/obo/CHEBI_23367', title='molecular entity')
    )

    # Add chemical attributes
    if data.get('inchi_key'):
        compound_obj.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(id='http://semanticscience.org/resource/CHEMINF_000059', title='InChiKey'),
            title='InChiKey', value=data.get('inchi_key')
        ))
    if data.get('inchi'):
        compound_obj.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(id='http://semanticscience.org/resource/CHEMINF_000113', title='InChi'),
            title='InChi', value=data.get('inchi')
        ))
    if data.get('smiles'):
        compound_obj.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(id='http://semanticscience.org/resource/CHEMINF_000018', title='SMILES'),
            title='SMILES', value=data.get('smiles')
        ))
    if data.get('mol_formula'):
        compound_obj.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(id='http://semanticscience.org/resource/CHEMINF_000037',
                                 title='IUPAC chemical formula'),
            title='IUPAC chemical formula', value=data.get('mol_formula')
        ))
    if data.get('exactmass'):
        compound_obj.has_quantitative_attribute.append(QuantitativeAttribute(
            rdf_type=DefinedTerm(id='http://semanticscience.org/resource/CHEMINF_000217',
                                 title='exact mass descriptor'),
            has_quantity_type='http://qudt.org/vocab/quantitykind/MolarMass',
            unit='https://qudt.org/vocab/unit/GM-PER-MOL',
            title='exact mass', value=data.get('exactmass')
        ))
    if data.get('iupacName'):
        compound_obj.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(id='http://semanticscience.org/resource/CHEMINF_000107', title='IUPAC name'),
            title='IUPAC name', value=data.get('iupacName')
        ))

    sample_obj = EvaluatedEntity(
        id=samp_id,
        rdf_type=DefinedTerm(id='http://purl.obolibrary.org/obo/CHEBI_59999', title='chemical substance'),
        title='evaluated sample',
        has_part=[compound_obj.id]
    )

    measurement_obj = DataGeneratingActivity(
        id=meas_id,
        rdf_type=DefinedTerm(
            id=data.get('measurement_technique_iri', 'http://purl.obolibrary.org/obo/OBI_0000070'),
            title=data.get('measurement_technique', 'assay')
        ),
        evaluated_entity=[sample_obj.id]
    )

    creators, publisher, legislation, language = (
        _get_authors(data), _get_publisher(data), _get_license(data, ds_id), _get_language(data)
    )

    dataset_obj = Dataset(
        id=ds_id,
        title=data.get('title'),
        description=_get_description(data),
        was_generated_by=[measurement_obj.id],
        identifier=ds_id,
        other_identifier=Identifier(notation=ds_id),
        is_about_entity=[sample_obj.id],
        release_date=data.get('metadata_created', '').split('T')[0],
        modification_date=data.get('metadata_modified', '').split('T')[0],
        landing_page=_get_url(data),
        conforms_to=Standard(title='DCAT-AP PLUS', description=SCHEMA_URL_DCAT_AP_PLUS),
        creator=creators,
        publisher=publisher,
        applicable_legislation=legislation,
        language=language
    )

    return _serialize_graph([dataset_obj, sample_obj, compound_obj, measurement_obj], schema_view, prefix_map)


def _build_chem_graph(
        data: Dict[str, Any],
        ds_id: str,
        cmp_id: str,
        samp_id: str,
        meas_id: str,
        schema_view: SchemaView,
        prefix_map: Dict[str, str]
) -> Graph:
    """Constructs the RDF Graph using ChemDCAT-AP classes."""
    compound_obj = ChemicalEntity(id=cmp_id)

    if data.get('inchi_key'):
        compound_obj.inchikey = InChIKey(title='InChiKey', value=data.get('inchi_key'))
    if data.get('inchi'):
        compound_obj.inchi = InChi(title='InChi', value=data.get('inchi'))
    if data.get('smiles'):
        compound_obj.smiles = SMILES(title='SMILES', value=data.get('smiles'))
    if data.get('mol_formula'):
        compound_obj.molecular_formula = MolecularFormula(title='IUPAC chemical formula', value=data.get('mol_formula'))
    if data.get('exactmass'):
        compound_obj.has_molar_mass = MolarMass(
            has_quantity_type='http://qudt.org/vocab/quantitykind/MolarMass',
            unit='https://qudt.org/vocab/unit/GM-PER-MOL',
            title='exact mass', value=data.get('exactmass')
        )
    if data.get('iupacName'):
        compound_obj.iupac_name = IUPACName(title='assigned IUPAC name', value=data.get('iupacName'))

    sample_obj = SubstanceSample(
        id=samp_id,
        rdf_type=DefinedTerm(id='http://purl.obolibrary.org/obo/CHEBI_59999', title='chemical substance'),
        title='evaluated sample',
        composed_of=[compound_obj.id]
    )

    measurement_obj = SubstanceSampleCharacterization(
        id=meas_id,
        rdf_type=DefinedTerm(
            id=data.get('measurement_technique_iri', 'http://purl.obolibrary.org/obo/OBI_0000070'),
            title=data.get('measurement_technique', 'assay')
        ),
        evaluated_entity=[sample_obj.id]
    )

    creators, publisher, legislation, language = (
        _get_authors(data), _get_publisher(data), _get_license(data, ds_id), _get_language(data)
    )

    dataset_obj = SubstanceSampleCharacterizationDataset(
        id=ds_id,
        title=data.get('title'),
        description=_get_description(data),
        was_generated_by=[measurement_obj.id],
        identifier=ds_id,
        other_identifier=Identifier(notation=ds_id),
        is_about_entity=[sample_obj.id],
        release_date=data.get('metadata_created', '').split('T')[0],
        modification_date=data.get('metadata_modified', '').split('T')[0],
        landing_page=_get_url(data),
        conforms_to=Standard(title='ChemDCAT-AP', description=SCHEMA_URL_CHEM_DCAT_AP),
        creator=creators,
        publisher=publisher,
        applicable_legislation=legislation,
        language=language
    )

    return _serialize_graph([dataset_obj, sample_obj, compound_obj, measurement_obj], schema_view, prefix_map)


def _serialize_graph(
        objects: List[Any],
        schema_view: SchemaView,
        prefix_map: Dict[str, str]
) -> Graph:
    """
    Serializes a list of LinkML objects into a single RDF Graph.

    Args:
        objects: List of LinkML dataclass instances.
        schema_view: The schema definition for context.
        prefix_map: Mapping of prefixes to URIs.

    Returns:
        An rdflib Graph object.
    """
    dumper = RDFLibDumper()
    graph = Graph()
    for obj in objects:
        graph += dumper.as_rdf_graph(obj, schemaview=schema_view, prefix_map=prefix_map)
    return graph


def transform_to_rdf(
        data: Dict[str, Any],
        shape: ShapeType,
        schema_view: SchemaView
) -> Optional[Graph]:
    """
    Main entry point for transforming a dataset dictionary into an RDF Graph.

    Args:
        data: The raw dataset metadata dictionary.
        shape: The target schema shape (DCAT-AP+ or ChemDCAT-AP).
        schema_view: The loaded SchemaView instance.

    Returns:
        An RDF Graph if successful, None otherwise.
    """
    # Determine Dataset ID
    if data.get('doi'):
        ds_id = f"https://doi.org/{data['doi']}"
    else:
        ds_id = f"https://search.nfdi4chem.de/dataset/{data['id'].strip()}"

    cmp_id = _build_compound_id(ds_id, data)
    samp_id = f"{ds_id}#sample"
    meas_id = f"{ds_id}#measurement"

    prefix_map = {
        'CHEMINF': 'http://semanticscience.org/resource/CHEMINF_',
        'CHMO': 'http://purl.obolibrary.org/obo/CHMO_',
        'CHEBI': 'http://purl.obolibrary.org/obo/CHEBI_'
    }

    try:
        if shape == ShapeType.DCAT_AP_PLUS:
            return _build_dcat_graph(data, ds_id, cmp_id, samp_id, meas_id, schema_view, prefix_map)
        elif shape == ShapeType.CHEM_DCAT_AP:
            return _build_chem_graph(data, ds_id, cmp_id, samp_id, meas_id, schema_view, prefix_map)
    except Exception as e:
        logger.error(f"Transformation failed for shape {shape.value}: {e}")
        return None

    return None


# --- Orchestrator ---

def process_datasets(ids: List[str], config: Config, schemas: Dict[ShapeType, SchemaView]) -> ProcessingResult:
    """
    Iterates through dataset IDs, transforms them, and saves output.

    Args:
        ids: List of dataset IDs to process.
        config: Runtime configuration.
        schemas: Dictionary of pre-loaded SchemaView instances.

    Returns:
        A ProcessingResult object containing statistics.
    """
    result = ProcessingResult(total=len(ids))
    logger.info(f"Starting processing of {result.total} datasets. Shapes: {[s.value for s in config.shapes]}")

    for i, ds_id in enumerate(ids, 1):
        if i % 100 == 0:
            logger.info(f"Progress: {i}/{result.total}")

        data = fetch_dataset(ds_id)
        if not data:
            logger.warning(f"Skipped '{ds_id}': Could not fetch dataset.")
            result.skipped_ids.append(ds_id)
            result.failed_all += 1
            continue

        print(f"[{i}/{result.total}] ID: {ds_id}")
        shape_failures: List[ShapeType] = []

        for shape in config.shapes:
            schema_view = schemas.get(shape)
            if not schema_view:
                logger.error(f"Schema missing for {shape.value}")
                shape_failures.append(shape)
                continue

            try:
                graph = transform_to_rdf(data, shape, schema_view)
                if graph:
                    _save_output(graph, ds_id, shape, config)
                else:
                    shape_failures.append(shape)
            except Exception as e:
                logger.error(f"Failed shape {shape.value} for {ds_id}: {e}")
                shape_failures.append(shape)

        if len(shape_failures) == len(config.shapes):
            result.skipped_ids.append(ds_id)
            result.failed_all += 1
        elif shape_failures:
            result.failed_partial += 1
        else:
            result.successful += 1

    return result


def _save_output(graph: Graph, dataset_id: str, shape: ShapeType, config: Config) -> None:
    """
    Saves the generated RDF graph to a file or prints to stdout.

    Args:
        graph: The RDF graph to save.
        dataset_id: The original dataset ID (used for filename).
        shape: The schema shape used.
        config: Runtime configuration.
    """
    ttl_content = graph.serialize(format='turtle')
    # Sanitize ID for filename
    safe_id = dataset_id.replace("/", "_").replace(":", "_").replace("#", "_")

    if config.output_format == OutputFormat.STDOUT:
        print(f"\n# --- BEGIN {shape.value.upper()} FOR {safe_id} ---")
        print(ttl_content)
        print("# --- END ---\n")
    else:
        output_dir = config.output_dir / shape.value.replace('-', '_')
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / f"{safe_id}_{shape.value}.ttl"
        file_path.write_text(ttl_content, encoding='utf-8')
        logger.debug(f"Written: {file_path}")


def parse_arguments() -> Config:
    """Parses command-line arguments and returns a Config object."""
    parser = argparse.ArgumentParser(
        description="NFDI4Chem to DCAT-AP+ / ChemDCAT-AP RDF Converter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py -f ids.txt
  python script.py --local-schema-dir ./schemas -of stdout
        """
    )
    parser.add_argument('-f', '--file', type=Path, help="Path to input file with dataset IDs")
    parser.add_argument('-sh', '--shape', type=ShapeType, nargs='+',
                        default=[ShapeType.DCAT_AP_PLUS, ShapeType.CHEM_DCAT_AP],
                        choices=list(ShapeType),
                        help="Schema shapes to generate (default: both)")
    parser.add_argument('-of', '--output_format', type=OutputFormat,
                        default=OutputFormat.FILE,
                        choices=list(OutputFormat),
                        help="Output destination (default: file)")
    parser.add_argument('--log-level', type=LogLevel,
                        default=LogLevel.CRITICAL,
                        choices=list(LogLevel),
                        help="Set the logging level (default: CRITICAL).")
    parser.add_argument('--local-schema-dir', type=Path,
                        help="Path to folder containing local schema YAMLs (fallback for ChemDCAT-AP)")

    args = parser.parse_args()

    return Config(
        input_file=args.file,
        shapes=args.shape,
        output_format=args.output_format,
        log_level=args.log_level,
        local_schema_dir=args.local_schema_dir
    )


def main() -> None:
    """Main entry point for the script."""
    config = parse_arguments()

    # Re-initialize logging with user-specified level
    global logger
    logger = setup_logging(config.log_level)

    try:
        # 1. Load Dataset IDs
        if config.input_file:
            dataset_ids = load_ids_from_file(config.input_file)
            if not dataset_ids:
                logger.warning(f"File '{config.input_file}' is empty.")
                return
        else:
            logger.info("No input file specified. Using default test IDs.")
            dataset_ids = DEFAULT_IDS

        # 2. Load Schemas
        schemas: Dict[ShapeType, SchemaView] = {}
        for shape in config.shapes:
            try:
                schemas[shape] = load_schema_view(shape, local_dir=config.local_schema_dir)
            except Exception as e:
                logger.critical(f"Failed to load schema {shape.value}: {e}")
                sys.exit(1)

        # 3. Process Datasets
        result = process_datasets(dataset_ids, config, schemas)

        # 4. Report Results
        print(
            f"\n✅ Complete. Successful: {result.successful}, Partial: {result.failed_partial}, Failed: {result.failed_all}")

        if result.skipped_ids:
            error_file = Path("failures.txt")
            with error_file.open("a", encoding='utf-8') as f:
                f.write(f"\n--- Run failed at {datetime.now()} ({len(result.skipped_ids)} items) ---\n")
                f.write("\n".join(result.skipped_ids) + "\n")
            print(f"⚠️  Failed IDs logged to {error_file}")

    except Exception as e:
        logger.exception(f"Critical failure: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
