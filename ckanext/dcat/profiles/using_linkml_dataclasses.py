import requests
from dcat_ap_plus.datamodel.dcat_ap_plus import (Agent,
                                                 Dataset,
                                                 DataGeneratingActivity,
                                                 DefinedTerm,
                                                 Document,
                                                 EvaluatedEntity,
                                                 Entity,
                                                 Concept,
                                                 Identifier,
                                                 LegalResource,
                                                 Standard,
                                                 QualitativeAttribute,
                                                 QuantitativeAttribute,
                                                 LinguisticSystem
                                                 )
from chem_dcat_ap.datamodel.chem_dcat_ap import (SubstanceSample,
                                                 SubstanceSampleCharacterizationDataset,
                                                 SubstanceSampleCharacterization,
                                                 InChi,
                                                 InChIKey,
                                                 IUPACName,
                                                 SMILES,
                                                 MolecularFormula,
                                                 MolarMass,
                                                 ChemicalEntity)
from linkml_runtime.dumpers import RDFLibDumper
from linkml_runtime.utils.schemaview import SchemaView
import os
import time
from typing import Dict, List, Any, Optional
import logging
import datetime
import argparse
import json

# --- Configure Logging with Full Stack Traces ---
logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("skipped_datasets.log", mode='a')
    ]
)
logger = logging.getLogger(__name__)

# --- Suppress verbose LinkML logs ---
logging.getLogger("linkml_runtime").setLevel(logging.WARNING)
logging.getLogger("linkml").setLevel(logging.WARNING)

# PubChem cache used by _get_pubchem_cid
_pubchem_cache = {}

def fetch_dataset_ids(url="https://search.nfdi4chem.de/api/3/action/package_list") -> List[str]:
    """
    Fetches the full list of dataset IDs from the API.
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if 'result' not in data:
            raise ValueError("API response does not contain 'result' key")

        result_data = data['result']

        if not isinstance(result_data, list):
            raise ValueError(f"Expected 'result' to be a list, got {type(result_data)}")

        logger.info(f"Fetched {len(result_data)} dataset IDs from {url}")
        return result_data

    except requests.exceptions.RequestException as err:
        logger.error(f"Failed to fetch dataset IDs: {err}")
        raise
    except ValueError as err:
        logger.error(f"Invalid JSON structure: {err}")
        raise


def fetch_single_dataset( dataset_id: str,
                          base_url="https://search.nfdi4chem.de/api/3/action/package_show?id=") -> Optional[Dict[str, Any]]:
    """
    Fetches a single dataset.
    Expected URL: base_url + dataset_id (e.g., .../api/3/action/package_show?id=quinine-proton)
    Returns the 'result' dict from the JSON response.
    """
    # The base_url is expected to include the query parameter prefix here based on your request
    # e.g., base_url = "https://search.nfdi4chem.de/api/3/action/package_show?id="
    url = f"{base_url}{dataset_id}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # CKAN wraps the actual package data in a 'result' key
        if 'result' in data:
            return data['result']

        # Fallback if structure is unexpected
        logger.warning(f"Response for '{dataset_id}' missing 'result' key. Returning root.")
        return data

    except requests.exceptions.RequestException as err:
        logger.warning(f"Network/HTTP error for '{dataset_id}': {err}")
        return None
    except ValueError as err:
        logger.warning(f"JSON decode error for '{dataset_id}': {err}")
        return None


def process_all_datasets(dataset_ids: List[str]) -> List[str]:
    """
    Iterates through the flat list of all dataset IDs, processes each, and logs failures with full traces.
    Returns a list of failed IDs for retry.
    """
    skipped_ids = []

    try:
        all_ids = dataset_ids
    except Exception as e:
        logger.critical(f"Aborting process: Could not fetch dataset list. {e}")
        return skipped_ids

    total_items = len(all_ids)
    logger.info(f"Starting processing of {total_items} datasets...")

    for i, ds_id in enumerate(all_ids):
        ds_id_str = str(ds_id)

        # Optional: Log progress every 100 items
        if (i + 1) % 100 == 0:
            logger.info(f"Progress: {i + 1}/{total_items} datasets processed.")

        data = fetch_single_dataset(ds_id_str)

        if data is None:
            skipped_ids.append(ds_id_str)
            logger.warning(f"Skipped '{ds_id_str}': Could not fetch dataset.")
        else:
            # ---------------------------------------------------------
            # YOUR PROCESSING LOGIC GOES HERE
            # ---------------------------------------------------------
            try:
                # --- Output for Verification ---
                print(f"[{i + 1}/{total_items}] ID: {ds_id_str}")

                # Execute the graph generation
                graph_from_dataset(data)

            except Exception as e:
                # CRITICAL CHANGE: Use logger.exception() to capture the full stack trace
                # This logs the error message AND the traceback to both console and file
                logger.exception(f"CRITICAL ERROR in graph_from_dataset for '{ds_id_str}': {e}")

                # Add to skipped list so you can identify which ones failed
                skipped_ids.append(ds_id_str)
            # ---------------------------------------------------------

    logger.info(f"Processing complete. Total: {total_items}, Skipped/Failed: {len(skipped_ids)}")
    return skipped_ids


def retry_failed_datasets(failed_ids: List[str], delay_seconds: int = 2) -> List[str]:
    """Attempts to re-fetch datasets that failed in the initial run."""
    if not failed_ids:
        logger.info("No failed IDs to retry.")
        return []

    logger.info(f"Starting retry process for {len(failed_ids)} datasets...")
    still_failed_ids = []

    for i, ds_id in enumerate(failed_ids):
        logger.info(f"Retry {i + 1}/{len(failed_ids)}: Attempting '{ds_id}'")

        data = fetch_single_dataset(ds_id)

        if data is not None:
            logger.info(f"Retry successful for '{ds_id}'")
            # Optionally re-run processing logic here
        else:
            logger.error(f"Retry FAILED for '{ds_id}'. Adding to permanent failure list.")
            still_failed_ids.append(ds_id)

        if i < len(failed_ids) - 1:
            time.sleep(delay_seconds)

    logger.info(f"Retry process complete. Permanently failed: {len(still_failed_ids)}")
    return still_failed_ids

def load_dataset_ids_from_file(file_path: str) -> List[str]:
    """
    Loads dataset IDs from a text file.
    Supports:
    1. JSON formatted list: ["id1", "id2"]
    2. Newline separated IDs: id1\nid2
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

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

    # Fallback to newline separated list
    ids = [line.strip() for line in content.splitlines() if line.strip()]
    logger.info(f"Loaded {len(ids)} IDs from newline-separated list in {file_path}")
    return ids


def _fetch_schema_yaml(purl: str) -> str:
    '''
    helper function to get the schema YAML files from their PURLs
    '''
    response = requests.get(purl, headers={"Accept": "application/yaml"}, allow_redirects=True)
    response.raise_for_status()
    return response.text


def _get_pubchem_cid(inchi_key=None, smiles=None):
    # 1. Normalize InChIKey to UPPERCASE immediately
    # InChIKeys are case-sensitive in URLs, and standard is Uppercase.
    if inchi_key:
        inchi_key = inchi_key.strip().upper()

    if smiles:
        smiles = smiles.strip()

    key = inchi_key or smiles

    if not key:
        return None

    # Check cache
    if key in _pubchem_cache:
        return _pubchem_cache[key]

    try:
        if inchi_key:
            # Now we are sure it is uppercase
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{inchi_key}/cids/TXT"
        elif smiles:
            # SMILES are generally case-sensitive but should be URL encoded by requests
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/cids/TXT"
        else:
            return None

        # Added headers to mimic a browser, sometimes helps with strict firewalls/proxies
        headers = {"Accept": "text/plain"}
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code == 200 and r.text.strip():
            cid = r.text.strip().split("\n")[0]
            # Basic validation: CID should be digits
            if cid.isdigit():
                _pubchem_cache[key] = cid
                return cid

        # If not 200 or empty, store None to prevent retrying same bad key
        _pubchem_cache[key] = None
        return None

    except Exception as e:
        # Optional: print(e) for debugging if needed
        _pubchem_cache[key] = None
        return None

def _creator_agents(dataset_dict):
    creators = []
    if dataset_dict.get("author"):
        for creator in dataset_dict.get("author").replace("., ", ".|").split("|"):
            creator = creator.strip()
            if creator:
                creators.append(Agent(name=creator,
                                      type=Concept(preferred_label='person',
                                                   description='A human being.')))
    else:
        pass

    return creators


def _get_authors(dataset_dict):
    """
    Helper function to account for multiple kinds of author strings that accounts for these cases:
        * 1: ["Yanagisawa", "K.", "Kaneko", "K.", ...]
        * 2: ["Anna Rudo", "Prof. Dr. Klaus-Peter Zeller", ...]
        * 3: ["Bisson J", "McAlpine JB", ...]
    """
    creators = []
    author_string = dataset_dict.get("author")

    if not author_string or not isinstance(author_string, str):
        return creators

    # 1. Split by comma to get fragments
    fragments = author_string.split(",")

    # Liste zur Sammlung der fertigen Namen
    full_names = []

    # Temporärer Puffer für den aktuellen Namen, den wir gerade bauen
    current_name_parts = []

    for fragment in fragments:
        clean_frag = fragment.strip()

        if not clean_frag:
            continue

        # Heuristik: Ist dieses Fragment wahrscheinlich eine Initiale?
        # Kriterien:
        # - Länge <= 2 (z.B. "K", "J.", "JB")
        # - ODER es besteht nur aus Buchstaben und Punkten und ist sehr kurz
        is_likely_initial = len(clean_frag) <= 2 and clean_frag.replace(".", "").isalpha()

        if is_likely_initial and full_names:
            # FALL 1 & 3: Dies ist eine Initiale, die zum VORHERIGEN Namen gehört.
            # Wir holen uns den letzten Namen aus der Liste und hängen die Initiale an.
            last_name = full_names.pop()

            # Entscheidung: Wollen wir ein Komma oder ein Leerzeichen zwischen Name und Initiale?
            # Standard wissenschaftliches Format: "Yanagisawa K." (Leerzeichen)
            # Das ursprüngliche Komma wird durch ein Leerzeichen ersetzt.
            combined_name = f"{last_name} {clean_frag}"
            full_names.append(combined_name)
        else:
            full_names.append(clean_frag)

    # 2. Nachbereitung: Bereinigung der gesammelten Namen
    final_creators = []

    for name in full_names:
        # Entferne Punkte, die nur als Listen-Ende dienen (z.B. "Pauli GF." -> "Pauli GF")
        # Aber behalte Punkte bei Initialen ("K.") oder Titeln ("Dr.")
        # Strategie: Wenn der Name auf "." endet, prüfen wir, ob davor eine Initiale steht.
        if name.endswith("."):
            parts = name.split()
            if parts:
                last_part = parts[-1]
                # Wenn der letzte Teil "K." oder "GF." ist (kurz + Punkt), ist der Punkt gewollt.
                # Wenn der letzte Teil "Sicker." ist (lang + Punkt), war es evtl. ein Satzpunkt.
                # Aber in "Bisson J." ist "J." kurz. In "Pauli GF." ist "GF." kurz.
                # In "Yanagisawa, K." -> wird zu "Yanagisawa K." (kurz).
                # Wir nehmen an: Wenn der letzte Teil <= 3 Zeichen ist (inkl. Punkt), ist der Punkt Teil der Initiale.
                if len(last_part) > 3:
                    # Wahrscheinlich ein Satzpunkt am Ende eines langen Namens
                    name = name[:-1]

        # Zusätzliche Bereinigung: Mehrfache Leerzeichen entfernen
        name = " ".join(name.split())

        if name:
            final_creators.append(Agent(
                name=name,
                type=Concept(preferred_label='person', description='A human being.')
            ))

    return final_creators

def _get_publisher(dataset_dict):
    org = dataset_dict.get("organization") or {}
    org_name = org.get("title") or org.get("display_name") or org.get("name")
    # these details cannot be used currently with DCAT-AP+ / ChemDCAT-AP
    # see also: https://github.com/nfdi-de/dcat-ap-plus/issues/84
    org_id = org.get("id")
    org_homepage = org.get("url")
    publisher = Agent(name=org_name,
                      type=Concept(
                          preferred_label='Academia/Scientific organisation',
                          description='http://purl.org/adms/publishertype/Academia-ScientificOrganisation'))

    return publisher

def _get_license(dataset_dict, dataset_id):
    applicable_legislation = []
    if dataset_dict.get('license_title'):
        title = dataset_dict.get('license_title')
        license_url = f"{dataset_id}#license_notspecified"
        if dataset_dict.get('license_id') != 'notspecified' and dataset_dict.get('license_url'):
            license_url = dataset_dict.get('license_url')
        applicable_legislation = [LegalResource(id=license_url, title=title)]
    else:
        pass

    return  applicable_legislation

def _get_language(dataset_dict):
    raw_lang = (dataset_dict.get('language') or '').strip().lower()
    if raw_lang in ('english', 'en', 'en-us', 'en-gb', 'eng'):
        code = 'en'
    elif raw_lang in ('deutsch', 'german', 'de'):
        code = 'de'
    elif raw_lang:
        code = raw_lang
    else:
        code = 'en'

    return LinguisticSystem(title=code, description=f"http://id.loc.gov/vocabulary/iso639-1/{code}")


def graph_from_dataset(dataset_dict):
    # Get the ID of the dataset
    # needed here in the beginning, to use as ID base/prefix for the IDs of the other nodes (sample, compound, etc.)
    if dataset_dict.get('doi'):
        dataset_id = 'https://doi.org/' + dataset_dict.get('doi')
    else:
        # if no DOI is present, we fallback to using the Search Service URL 
        dataset_id = f"https://search.nfdi4chem.de/dataset/{dataset_dict.get('id').strip()}"

    ### Instantiation of the DCAT-AP+ / ChemDCAT-AP Python dataclasses
    ### the order of instantiation matters if done like this and not in helper functions, as they reference each other

    # Default to local IRI
    compound_id = f"{dataset_id}#sample_compound"

    # Only try PubChem if we have data
    inchi_key = dataset_dict.get("inchi_key")
    smiles = dataset_dict.get("smiles")
    if inchi_key or smiles:
        cid = _get_pubchem_cid(inchi_key=inchi_key, smiles=smiles)

        # 2. ONLY overwrite if we got a valid CID (not None)
        if cid:
            compound_id = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        # else: keep the default #sample_compound

    # Instantiate the evaluated compound in DCAT-AP
    compound = Entity(
        id=compound_id,
        rdf_type=DefinedTerm(id='http://purl.obolibrary.org/obo/CHEBI_23367',
                             title='molecular entity'),
    )
    # Instantiate the evaluated compound in ChemDCAT-AP
    compound_chem = ChemicalEntity(id=compound_id)
    # add inchi_key to the evaluated compound if it is present
    if dataset_dict.get('inchi_key'):
        compound.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(
                id='http://semanticscience.org/resource/CHEMINF_000059',
                title='InChiKey'),
            title='InChiKey',
            value=dataset_dict.get('inchi_key')))
        # ChemDCAT-AP
        compound_chem.inchikey = InChIKey(title='InChiKey',
                                          value=dataset_dict.get('inchi_key'))
    # add inchi to the evaluated compound if it is present
    if dataset_dict.get('inchi'):
        compound.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(
                id='http://semanticscience.org/resource/CHEMINF_000113',
                title='InChi'),
            title='InChi',
            value=dataset_dict.get('inchi')))
        # ChemDCAT-AP
        compound_chem.inchi=InChi(title='InChi',
                                  value=dataset_dict.get('inchi'))
    # add smiles to the evaluated compound if it is present
    if dataset_dict.get('smiles'):
        compound.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(
                id='http://semanticscience.org/resource/CHEMINF_000018',
                title='SMILES'),
            title='SMILES',
            value=dataset_dict.get('smiles')))
        # ChemDCAT-AP
        compound_chem.smiles=SMILES(title='SMILES',
                                    value=dataset_dict.get('smiles'))
    # add molecular_formular to the evaluated compound if it is present
    if dataset_dict.get('mol_formula'):
        # DCAT-AP+
        compound.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(
                id='http://semanticscience.org/resource/CHEMINF_000037',
                title='IUPAC chemical formula'),
            title='IUPAC chemical formula',
            value=dataset_dict.get('mol_formula')))
        # ChemDCAT-AP
        compound_chem.molecular_formula = MolecularFormula(title='IUPAC chemical formula',
                                                           value=dataset_dict.get('mol_formula'))
    # add exactmass to the evaluated compound if it is present
    if dataset_dict.get('exactmass'):
        # DCAT-AP+
        compound.has_quantitative_attribute.append(QuantitativeAttribute(
            rdf_type=DefinedTerm(
                id='http://semanticscience.org/resource/CHEMINF_000217',
                title='exact mass descriptor'),
            has_quantity_type='http://qudt.org/vocab/quantitykind/MolarMass',
            unit='https://qudt.org/vocab/unit/GM-PER-MOL',
            title='exact mass',
            value=dataset_dict.get('exactmass')))
        # ChemDCAT-AP
        compound_chem.has_molar_mass = MolarMass(has_quantity_type='http://qudt.org/vocab/quantitykind/MolarMass',
                                                 unit='https://qudt.org/vocab/unit/GM-PER-MOL',
                                                 title='exact mass',
                                                 value=dataset_dict.get('exactmass'))
    # add iupacName to the evaluated compound if it is present
    if dataset_dict.get('iupacName'):
        # DCAT-AP+
        compound.has_qualitative_attribute.append(QualitativeAttribute(
            rdf_type=DefinedTerm(
                id='http://semanticscience.org/resource/CHEMINF_000107',
                title='IUPAC name'),
            title='IUPAC name',
            value=dataset_dict.get('iupacName')))
        #ChemDCAT-AP
        compound_chem.iupac_name = IUPACName(title='assigned IUPAC name',
                                             value=dataset_dict.get('iupacName'))

    # Instantiate the evaluated sample in DCAT-AP+
    # TODO: We used a fake ID, as the real one is not within the example dataset, but might be in the source data.
    # TODO: Do we need different instantiation steps/conditions based on where the metadata comes from?
    sample_id = f"{dataset_id}#sample"
    sample = EvaluatedEntity(
        id=sample_id,
        # all samples are chemical substances in our context -> we hard code the type in the DCAT-AP+ profile like this
        rdf_type=DefinedTerm(id='http://purl.obolibrary.org/obo/CHEBI_59999', title='chemical substance'),
        # default title for now, until we can harvest sample names from the repos, e.g. "CRS-56724"
        title='evaluated sample',
        has_part=[compound.id]
    )
    # Instantiate the evaluated compound in ChemDCAT-AP
    sample_chem = SubstanceSample(
        id=sample_id,
        # all samples are chemical substances in our context, SubstanceSample is already mapped to SIO:001378 (analyte)
        # -> we hard code as an additional type assertion CHEBI's 'chemical substance' like this
        rdf_type=DefinedTerm(id='http://purl.obolibrary.org/obo/CHEBI_59999', title='chemical substance'),
        # default title for now, until we can harvest sample names from the repos, e.g. "CRS-56724"
        title='evaluated sample',
        composed_of=[compound_chem.id]
    )

    # Instantiate the measurement process/activity
    # --- measurement (Activity) ---
    measurement_id = f"{dataset_id}#measurement"
    if dataset_dict.get('measurement_technique_iri'):
        # in DCAT - AP +
        measurement = DataGeneratingActivity(
            id=measurement_id,  # required
            rdf_type=DefinedTerm(
                id=dataset_dict['measurement_technique_iri'],
                title=dataset_dict.get('measurement_technique')
            ),
            evaluated_entity=[sample.id]
        )
        # in ChemDCAT-AP
        measurement_chem = SubstanceSampleCharacterization(
            id=measurement_id,  # required
            rdf_type=DefinedTerm(
                id=dataset_dict['measurement_technique_iri'],
                title=dataset_dict.get('measurement_technique')
            ),
            evaluated_entity=[sample_chem.id]
        )
    else:
        # in DCAT-AP+
        measurement = DataGeneratingActivity(
            id=measurement_id,  # required
            rdf_type=DefinedTerm(
                id='http://purl.obolibrary.org/obo/OBI_0000070',
                title='assay'
            ),
            evaluated_entity=[sample.id]
        )
        # in ChemDCAT-AP
        measurement_chem = SubstanceSampleCharacterization(
            id=measurement_id,  # required
            rdf_type=DefinedTerm(
                id='http://purl.obolibrary.org/obo/OBI_0000070',
                title='assay'
            ),
            evaluated_entity=[sample_chem.id]
        )

    # --- dataset ---
    dataset = Dataset(
        id=dataset_id,
        title=dataset_dict.get('title'),
        description=dataset_dict.get('notes').strip() or 'No description',
        was_generated_by=[measurement.id],
        identifier=dataset_id,
        other_identifier=Identifier(notation=dataset_id),
        is_about_entity=[sample.id],
        release_date=dataset_dict.get('metadata_created').split('T')[0],
        modification_date=dataset_dict.get('metadata_modified').split('T')[0],
        landing_page = [Document(id=dataset_dict.get('url'))],
        conforms_to=Standard(title='DCAT-AP PLUS', description='https://w3id.org/nfdi-de/dcat-ap-plus/'),
        creator=_get_authors(dataset_dict),
        publisher=_get_publisher(dataset_dict),
        applicable_legislation=_get_license(dataset_dict, dataset_id),
        language=_get_language(dataset_dict)
    )

    dataset_chem = SubstanceSampleCharacterizationDataset(
        id=dataset_id,
        title=dataset_dict.get('title'),
        description=dataset_dict.get('notes').strip() or 'No description',
        was_generated_by=[measurement_chem.id],
        identifier=dataset_id,
        other_identifier=Identifier(notation=dataset_id),
        is_about_entity=[sample_chem.id],
        release_date = dataset_dict.get('metadata_created').split('T')[0],
        modification_date = dataset_dict.get('metadata_modified').split('T')[0],
        landing_page=[Document(id=dataset_dict.get('url'))],
        conforms_to=Standard(title='ChemDCAT-AP', description='https://w3id.org/nfdi-de/dcat-ap-plus/chemistry/'),
        creator=_get_authors(dataset_dict),
        publisher=_get_publisher(dataset_dict),
        applicable_legislation=_get_license(dataset_dict, dataset_id),
        language=_get_language(dataset_dict)
    )


    ### Dump dataset using LinkML's RDFLibDumper
    # In this prefix map we define all prefixes used that need to be passed to the RDFLibDumper to dump the graph
    prefix_map = {#'@base': 'https://search.nfdi4chem.de/dataset/',
                  'CHEMINF': 'http://semanticscience.org/resource/CHEMINF_',
                  'CHMO':'http://purl.obolibrary.org/obo/CHMO_',
                  'CHEBI': 'http://purl.obolibrary.org/obo/CHEBI_'
                  }
    # Dump each LinkML object you want in the dcat_ap_plus_graph
    rdf_dumper = RDFLibDumper()
    sv_dcat_ap_plus = SchemaView(_fetch_schema_yaml("https://w3id.org/nfdi-de/dcat-ap-plus/"), merge_imports=True)

    dcat_ap_plus_graph = rdf_dumper.as_rdf_graph(dataset, schemaview=sv_dcat_ap_plus, prefix_map=prefix_map)
    dcat_ap_plus_graph += rdf_dumper.as_rdf_graph(sample, schemaview=sv_dcat_ap_plus, prefix_map=prefix_map)
    dcat_ap_plus_graph += rdf_dumper.as_rdf_graph(compound, schemaview=sv_dcat_ap_plus, prefix_map=prefix_map)
    dcat_ap_plus_graph += rdf_dumper.as_rdf_graph(measurement, schemaview=sv_dcat_ap_plus, prefix_map=prefix_map)

    # Dump each LinkML object you want in the chem_dcat_ap_graph
    rdf_dumper2 = RDFLibDumper()
    sv_chem_dcat_ap = SchemaView("../schemas/chem_dcat_ap.yaml", merge_imports=True)

    chem_dcat_ap_graph = rdf_dumper2.as_rdf_graph(dataset_chem, schemaview=sv_chem_dcat_ap, prefix_map=prefix_map)
    chem_dcat_ap_graph += rdf_dumper2.as_rdf_graph(sample_chem, schemaview=sv_chem_dcat_ap, prefix_map=prefix_map)
    chem_dcat_ap_graph += rdf_dumper.as_rdf_graph(compound_chem, schemaview=sv_chem_dcat_ap, prefix_map=prefix_map)
    chem_dcat_ap_graph += rdf_dumper2.as_rdf_graph(measurement_chem, schemaview=sv_chem_dcat_ap, prefix_map=prefix_map)

    # --- FILE WRITING LOGIC ---
    safe_id = dataset_dict.get('id').strip()
    output_dir = "output"

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    dcat_file = os.path.join(output_dir, 'dcat_ap_plus', f"{safe_id}_dcat-ap-plus.ttl")
    chem_file = os.path.join(output_dir, 'chem_dcat_ap',f"{safe_id}_chem-dcat-ap.ttl")

    with open(dcat_file, 'w', encoding='utf-8') as f:
        f.write(dcat_ap_plus_graph.serialize(format='ttl'))

    with open(chem_file, 'w', encoding='utf-8') as f:
        f.write(chem_dcat_ap_graph.serialize(format='ttl'))

    logger.info(f"Files written for {safe_id}: {os.path.basename(dcat_file)}, {os.path.basename(chem_file)}")


def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Process NFDI4Chem datasets into DCAT-AP+ & ChemDCAT-AP RDF.")
    parser.add_argument('-f', '--file', type=str,
                        help="Path to a text file containing a list of dataset IDs (JSON or newline separated).")

    args = parser.parse_args()

    dataset_ids = []

    # Determine source of IDs: File vs API
    if args.file:
        try:
            dataset_ids = load_dataset_ids_from_file(args.file)
            if not dataset_ids:
                logger.warning(f"File '{args.file}' is empty or contains no valid IDs.")
                return
        except Exception as e:
            logger.error(f"Failed to load input file: {e}")
            return
    else:
        logger.info("No input file specified. Fetching all dataset IDs from API...")
        try:
            dataset_ids = fetch_dataset_ids()
        except Exception as e:
            logger.critical(f"Aborting process: Could not fetch dataset list. {e}")
            return

    # Run processing
    failed_ids = process_all_datasets(dataset_ids)

    # Handle failures
    if failed_ids:
        print(f"\n⚠️  Attention Required: {len(failed_ids)} datasets could not be processed.")

        error_file = os.path.join("failures.txt")

        # Append mode is safe for parallel processes
        with open(error_file, "a") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n--- Run failed at {timestamp} ({len(failed_ids)} items) ---\n")

            for item in failed_ids:
                f.write(f"{item}\n")

        print(f"Permanent failures appended to {error_file}")
    else:
        print("\n✅ All datasets processed successfully on first pass!")


if __name__ == '__main__':
    main()