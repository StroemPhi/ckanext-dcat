import json
from decimal import Decimal, DecimalException
import requests
from rdflib import term, URIRef, BNode, Literal, Graph
import ckantoolkit as toolkit

# from ckan.lib.munge import munge_tag
import logging

from ckanext.dcat.profiles.dcat_4c_ap import (Agent,
                                              Concept,
                                              Dataset,
                                              DataGeneratingActivity,
                                              DefinedTerm,
                                              Document,
                                              EvaluatedEntity,
                                              Entity,
                                              Identifier,
                                              LinguisticSystem,
                                              Standard,
                                              QualitativeAttribute,
                                              QuantitativeAttribute)
from . import EuropeanDCATAPProfile, EuropeanDCATAP2Profile

log = logging.getLogger(__name__)

from ckanext.dcat.utils import (
    resource_uri,
    DCAT_EXPOSE_SUBCATALOGS,
    DCAT_CLEAN_TAGS,
    publisher_uri_organization_fallback,
)
from .base import RDFProfile, URIRefOrLiteral, CleanedURIRef
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
    CHEMINF,  # this
    CHMO,  # this
    OBI,
    IAO,
    PROV,
    CHEBI,
    NMR,
    QUDT,
    NCIT,
    FIX,
    namespaces
)
from linkml_runtime.dumpers import RDFLibDumper
from linkml_runtime.utils.schemaview import SchemaView


class DCATNFDi4ChemProfile(EuropeanDCATAPProfile):
    """
    An RDF profile extending DCAT-AP for NFDI4Chem

    Extends the EuropeanDCATAPProfile to support NFDI4Chem-specific fields.
    """

    def parse_dataset(self, dataset_dict, dataset_ref):
        # TODO: Create a parser
        log.debug('parsing dataset for test ')
        dataset_dict['title'] = str(dataset_ref.value(DCT.title))
        dataset_dict['notes'] = str(dataset_ref.value(DCT.description))
        dataset_dict['doi'] = str(dataset_ref.value(DCT.identifier))
        dataset_dict['language'] = [
            str(theme.value(SKOS.prefLabel)) for theme in dataset_ref.objects(DCAT.theme)
        ]
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
                        creators.append = Agent(name=creator,
                                                type=Concept(preferred_label='person',
                                                             description='A human being.'))
            else:
                pass
        except Exception as e:

            log.error(e)
        return creators

    def _get_pubchem_cid(self, inchi_key=None, smiles=None):
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

    def _fetch_schema_yaml(purl: str) -> str:
        '''
        helper function to get the schema YAML files from their PURLs
        '''
        response = requests.get(purl, headers={"Accept": "application/yaml"}, allow_redirects=True)
        response.raise_for_status()
        return response.text

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

        cid = self._get_pubchem_cid(inchi_key=inchi_key, smiles=smiles)

        if cid:
            compound_id = f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
        else:
            compound_id = f"{dataset_id}#sample_compound"

        compound = Entity(id=compound_id)

        if dataset_dict.get("inchi_key"):
            compound.has_qualitative_attribute.append(QualitativeAttribute(
                rdf_type=DefinedTerm(
                    id='http://semanticscience.org/resource/CHEMINF_000059',
                    title='InChiKey'),
                title="assigned InChIKey",
                value=dataset_dict.get("inchi_key")
            ))

        if dataset_dict.get("inchi"):
            compound.has_qualitative_attribute.append(QualitativeAttribute(
                rdf_type=DefinedTerm(
                    id='http://semanticscience.org/resource/CHEMINF_000113',
                    title='InChi'),
                title="assigned InChI",
                value=dataset_dict.get("inchi")
            ))

        if dataset_dict.get("smiles"):
            compound.has_qualitative_attribute.append(QualitativeAttribute(
                rdf_type=DefinedTerm(
                    id='http://semanticscience.org/resource/CHEMINF_000018',
                    title='SMILES'),
                title="assigned SMILES",
                value=dataset_dict.get("smiles")
            ))

        if dataset_dict.get("mol_formula"):
            compound.has_qualitative_attribute.append(QualitativeAttribute(
                rdf_type=DefinedTerm(
                    id='http://semanticscience.org/resource/CHEMINF_000037',
                    title='IUPAC chemical formula'),
                title="assigned IUPAC chemical formula",
                value=dataset_dict.get("mol_formula")
            ))

        if dataset_dict.get("exactmass"):
            compound.has_qualitative_attribute.append(QuantitativeAttribute(
                rdf_type=DefinedTerm(
                    id='http://semanticscience.org/resource/CHEMINF_000217',
                    title='exact mass descriptor'),
                has_quantity_type="http://qudt.org/vocab/quantitykind/MolarMass",
                unit="https://qudt.org/vocab/unit/GM-PER-MOL",
                title="assigned exact mass",
                value=dataset_dict.get("exactmass")
            ))

        if dataset_dict.get("iupacName"):
            compound.has_qualitative_attribute.append(QualitativeAttribute(
                rdf_type=DefinedTerm(
                    id='http://semanticscience.org/resource/CHEMINF_000107',
                    title='IUPAC name'),
                title="assigned IUPAC name",
                value=dataset_dict.get("iupacName")
            ))

        # -------------------------
        # Sample
        # -------------------------
        sample = EvaluatedEntity(
            id=f'{dataset_id}#sample',
            title='evaluated sample',
            has_part=[compound.id]
        )

        # -------------------------
        # Measurement
        # -------------------------
        technique_iri = dataset_dict.get("measurement_technique_iri") or "http://purl.obolibrary.org/obo/OBI_0000070"
        technique_label = dataset_dict.get("measurement_technique") or "assay"
        measurement = DataGeneratingActivity(
            id=f"{dataset_id}#measurement",
            rdf_type=DefinedTerm(
                id=technique_iri,
                title=technique_label
            ),
            evaluated_entity=[sample.id]
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
        dataset = Dataset(
            id=dataset_id,
            title=dataset_dict.get("title"),
            description=dataset_dict.get("notes") or "No description",
            identifier=dataset_id,
            other_identifier=Identifier(notation=dataset_id),
            release_date=dataset_dict.get('metadata_created').split('T')[0],
            modification_date=dataset_dict.get('metadata_modified').split('T')[0],
            landing_page=Document(id=dataset_dict.get('url')),
            creator=self._creator_agents(dataset_dict),
            language=language,
            publisher=publisher,
            conforms_to=Standard(title='ChemDCAT-AP', description='https://w3id.org/nfdi-de/dcat-ap-plus/chemistry/'),
            was_generated_by=[measurement.id],
            is_about_entity=[sample.id],
        )
        sv_dcat_ap_plus = SchemaView(_fetch_schema_yaml("https://w3id.org/nfdi-de/dcat-ap-plus/"), merge_imports=True)

        rdf_dumper = RDFLibDumper()

        prefix_map = {'@base': 'https://search.nfdi4chem.de/dataset/',
                      'CHEMINF': 'http://semanticscience.org/resource/CHEMINF_',
                      'CHMO': 'http://purl.obolibrary.org/obo/CHMO_',
                      'CHEBI': 'http://purl.obolibrary.org/obo/CHEBI_'
                      }

        try:
            graph = rdf_dumper.as_rdf_graph(dataset, schemaview=sv_dcat_ap_plus, prefix_map = prefix_map)
            graph += rdf_dumper.as_rdf_graph(sample, schemaview=sv_dcat_ap_plus, prefix_map = prefix_map)
            graph += rdf_dumper.as_rdf_graph(compound, schemaview=sv_dcat_ap_plus, prefix_map = prefix_map)
            graph += rdf_dumper.as_rdf_graph(measurement, schemaview=sv_dcat_ap_plus, prefix_map = prefix_map)
        except Exception as e:
            log.warning("DCAT-AP PLUS serialization skipped: %s", e)
            return None

        for triple in graph:
            self.g.add(triple)


