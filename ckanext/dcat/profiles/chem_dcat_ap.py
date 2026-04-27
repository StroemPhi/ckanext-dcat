import requests
import json
from decimal import Decimal, DecimalException
from rdflib import term, URIRef, BNode, Literal, Graph
import ckantoolkit as toolkit
from .dcat_4c_ap import (Agent,
                         LinguisticSystem,
                         LegalResource,
                         Concept,
                         Standard,
                         Document,
                         DefinedTerm,
                         SubstanceSample,
                         SubstanceSampleCharacterizationDataset,
                         SubstanceSampleCharacterization,
                         InChi, InChIKey, IUPACName, SMILES, MolecularFormula, MolarMass,
                         ChemicalEntity,
                         Identifier)

from .base import (
    RDF,
    XSD,
    SKOS,
    RDFS,
    DCAT,
    DCT,
    ADMS,
    VCARD,
    FOAF,
    SCHEMA,
    NFDI,
    CHEMINF,
    CHMO,
    OBI,
    IAO,
    PROV,
    CHEBI,
    NMR,
    QUDT,
    NCIT,
    FIX,
    namespaces,
)

from linkml_runtime.dumpers import RDFLibDumper
from linkml_runtime.utils.schemaview import SchemaView
import yaml

from . import EuropeanDCATAPProfile, EuropeanDCATAP2Profile

from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS

import logging
log = logging.getLogger(__name__)


class ChemDCATAPProfile(EuropeanDCATAPProfile):
    def parse_dataset(self, dataset_dict, dataset_ref):
        log.debug("parsing dataset for chem dcat ap")
        dataset_dict["title"] = str(dataset_ref.value(DCT.title) or "")
        dataset_dict["notes"] = str(dataset_ref.value(DCT.description) or "")
        dataset_dict["doi"] = str(dataset_ref.value(DCT.identifier) or "")
        dataset_dict["language"] = str(dataset_ref.value(DCT.language) or "")
        return dataset_dict


    def _dataset_identity(self, dataset_dict):
        # use the DOI as the IRI of a dataset
        if dataset_dict.get("doi"):
            dataset_id = "https://doi.org/" + dataset_dict.get("doi")
        # if no DOI to the source repo exists, we use the Search Service ID + base prefix as IRI
        else:
            dataset_id = dataset_dict.get("id").strip()
        return dataset_id


    def _normalize_language_code(self, raw_lang):
        raw_lang = (raw_lang or "").strip().lower()
        if raw_lang in ("english", "en", "en-us", "en-gb", "eng"):
            return "en"
        elif raw_lang in ("deutsch", "german", "de"):
            return "de"
        elif raw_lang:
            return raw_lang
        else:
            return "en"


    def _creator_agents(self, dataset_dict):
        creators = []
        try:
            if dataset_dict.get("author"):
                for creator in dataset_dict.get("author").replace("., ", ".|").split("|"):
                    creator = creator.strip()
                    if creator:
                        creators.append(Agent(name=creator,
                                                type=Concept(preferred_label='person',
                                                             description='A human being.')))
            else:
                pass
        except Exception as e:

            log.error(e)
        return creators


    def _get_pubchem_cid(self,inchi_key=None, smiles=None):
        key = inchi_key or smiles
        _pubchem_cache = {}
        if key in _pubchem_cache:
            return _pubchem_cache[key]

        try:
            if inchi_key:
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchikey/{inchi_key}/cids/TXT"
            elif smiles:
                url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/cids/TXT"
            else:
                return None

            r = requests.get(url, timeout=5)

            if r.status_code == 200:
                cid = r.text.strip().split("\n")[0]
                _pubchem_cache[key] = cid
                return cid

        except Exception:
            return None

        _pubchem_cache[key] = None
        return None


    def graph_from_dataset(self, dataset_dict, dataset_ref):

        # Question from Philip to Bhavin: why do we need this here?
        # So far we only use the prefix map passed to the RDFLibDumper
        for prefix, namespace in namespaces.items():
            self.g.bind(prefix, namespace)

        dataset_id = self._dataset_identity(dataset_dict)

        # -------------------------
        # Compound
        # -------------------------
        inchi_key = dataset_dict.get("inchi_key")
        smiles = dataset_dict.get("smiles")

        cid = self._get_pubchem_cid(inchi_key= inchi_key, smiles=smiles)

        if cid:
            compound_id = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        else:
            compound_id = f"{dataset_id}#sample_compound"

        compound_kwargs = {
            "id": compound_id,
        }

        if dataset_dict.get("inchi_key"):
            compound_kwargs["inchikey"] = InChIKey(
                title="assigned InChIKey",
                value=dataset_dict.get("inchi_key")
            )

        if dataset_dict.get("inchi"):
            compound_kwargs["inchi"] = InChi(
                title="assigned InChI",
                value=dataset_dict.get("inchi")
            )

        if dataset_dict.get("smiles"):
            compound_kwargs["smiles"] = SMILES(
                title="assigned SMILES",
                value=dataset_dict.get("smiles")
            )

        if dataset_dict.get("mol_formula"):
            compound_kwargs["molecular_formula"] = MolecularFormula(
                title="assigned IUPAC chemical formula",
                value=dataset_dict.get("mol_formula")
            )

        if dataset_dict.get("exactmass"):
            compound_kwargs["has_molar_mass"] = MolarMass(
                has_quantity_type="http://qudt.org/vocab/quantitykind/MolarMass",
                unit="https://qudt.org/vocab/unit/GM-PER-MOL",
                title="assigned exact mass",
                value=dataset_dict.get("exactmass")
            )

        if dataset_dict.get("iupacName"):
            compound_kwargs["iupac_name"] = IUPACName(
                title="assigned IUPAC name",
                value=dataset_dict.get("iupacName")
            )

        compound_chem = ChemicalEntity(**compound_kwargs)

        # -------------------------
        # Sample
        # -------------------------
        sample_chem = SubstanceSample(
            id=f"{dataset_id}#sample",
            title="evaluated sample",
            composed_of=[compound_chem.id]
        )

        # -------------------------
        # Measurement
        # -------------------------
        if dataset_dict.get("measurement_technique_iri"):
            technique_iri = dataset_dict.get("measurement_technique_iri")
            technique_label = dataset_dict.get("measurement_technique")
        else:
            technique_iri = "http://purl.obolibrary.org/obo/OBI_0000070"
            technique_label =  "assay"
        measurement_chem = SubstanceSampleCharacterization(
            id=f"{dataset_id}#measurement",
            rdf_type=DefinedTerm(
                id=technique_iri,
                title=technique_label
            ),
            evaluated_entity=[sample_chem.id]
        )


        # -------------------------
        # Language
        # -------------------------
        code = self._normalize_language_code(dataset_dict.get("language"))
        lang_uri = f"http://id.loc.gov/vocabulary/iso639-1/{code}"
        language = LinguisticSystem(title=code,
                                    description=lang_uri)


        # -------------------------
        # Publisher
        # -------------------------
        org = dataset_dict.get("organization") or {}
        org_name = org.get("title") or org.get("display_name") or org.get("name")
        # org_id & org_homepage cannot yet be used with DCAT-AP+ / ChemDCAT-AP
        # see also: https://github.com/nfdi-de/dcat-ap-plus/issues/84
        org_id = org.get("id")
        org_homepage = org.get("url")

        publisher = Agent(name=org_name,
                          type=Concept(preferred_label='Academia/Scientific organisation',
                                       description='http://purl.org/adms/publishertype/Academia-ScientificOrganisation'))


        # -------------------------
        # Dataset
        # -------------------------
        dataset_chem = SubstanceSampleCharacterizationDataset(
            id=dataset_id,
            title=dataset_dict.get("title"),
            description=dataset_dict.get("notes") or "No description",
            identifier=dataset_id,
            other_identifier=Identifier(notation=dataset_id),
            release_date = dataset_dict.get('metadata_created').split('T')[0],
            modification_date = dataset_dict.get('metadata_modified').split('T')[0],
            creator= self._creator_agents(dataset_dict),
            language=[language],
            publisher = publisher,
            conforms_to=Standard(title='ChemDCAT-AP', description='https://w3id.org/nfdi-de/dcat-ap-plus/chemistry/'),
            was_generated_by=[measurement_chem.id],
            is_about_entity=[sample_chem.id],
        )

        # -------------------------
        # Landing Page
        # -------------------------
        if dataset_dict.get('url'):
            dataset_chem.landing_page = [Document(id=dataset_dict.get('url'))]

        # -------------------------
        # License
        # -------------------------
        if dataset_dict.get('license_title'):
            title = dataset_dict.get('license_title')
            license_url = f"{dataset_id}#license_notspecified"
            if dataset_dict.get('license_id') != 'notspecified' and dataset_dict.get('license_url'):
                license_url = dataset_dict.get('license_url')
            dataset_chem.applicable_legislation = [LegalResource(id=license_url, title=title)]
        else:
            pass

        # -------------------------
        # Build Graph
        # -------------------------
        sv_chem_dcat_ap = SchemaView(
            "/usr/lib/ckan/default/src/ckanext-dcat/ckanext/dcat/schemas/chem_dcat_ap.yaml",
            merge_imports=True
        )

        rdf_dumper = RDFLibDumper()

        prefix_map = {'@base': 'https://search.nfdi4chem.de/dataset/',
                      'CHEMINF': 'http://semanticscience.org/resource/CHEMINF_',
                      'CHMO': 'http://purl.obolibrary.org/obo/CHMO_',
                      'CHEBI': 'http://purl.obolibrary.org/obo/CHEBI_'
                      }

        try:
            graph = rdf_dumper.as_rdf_graph(dataset_chem, schemaview=sv_chem_dcat_ap, prefix_map = prefix_map)
            graph += rdf_dumper.as_rdf_graph(sample_chem, schemaview=sv_chem_dcat_ap, prefix_map = prefix_map)
            graph += rdf_dumper.as_rdf_graph(compound_chem, schemaview=sv_chem_dcat_ap, prefix_map = prefix_map)
            graph += rdf_dumper.as_rdf_graph(measurement_chem, schemaview=sv_chem_dcat_ap, prefix_map = prefix_map)
        except Exception as e:
            log.warning("ChemDCAT-AP serialization skipped: %s", e)
            return None

        for triple in graph:
            self.g.add(triple)


