import json
from decimal import Decimal, DecimalException

from rdflib import term, URIRef, BNode, Literal, Graph
import ckantoolkit as toolkit

#from ckan.lib.munge import munge_tag
import logging

from .dcat_4c_ap import AnalysisDataset, Identifier, LinguisticSystem, Document

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
    CHEMINF, # this
    CHMO, # this
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

class DCATNFDi4ChemProfile(RDFProfile):
    """
    An RDF profile extending DCAT-AP for NFDI4Chem

    Extends the EuropeanDCATAPProfile to support NFDI4Chem-specific fields.
    """

    def parse_dataset(self, dataset_dict, dataset_ref):
        dataset_dict['title'] = str(dataset_ref.value(DCT.title))
        dataset_dict['notes'] = str(dataset_ref.value(DCT.description))
        dataset_dict['doi'] = str(dataset_ref.value(DCT.identifier))
        dataset_dict['language'] = [
            str(theme.value(SKOS.prefLabel)) for theme in dataset_ref.objects(DCAT.theme)
        ]
        return dataset_dict


    def graph_from_dataset(self, dataset_dict, dataset_ref):
        #g = self.g
        g = RDFLibDumper()
        dataset_dict = {
            'author': 'Yanagisawa, K., Kaneko, K., Ikeda, H., Iwata, S., Muranaka, A., Koshino, H., Nagao, N., Watari, S., Nishimura, S., Shinzato, N., Onaka, H., Kakeya, H.',
            'author_email': None, 
            'creator_user_id': '8a5c874c-b5ab-4df4-87d3-dfdc40fe20f6',
            'doi': '10.57992/nmrxiv.p85.s729.d3596',
            'exactmass': '',
            'id': 'nmrxiv-d3596',
            'inchi': 'InChI=1S/C21H23NO7/c1-9(2)3-4-14-16-10(5-11(29-14)7-15(24)25)6-12-17(21(16)28)19(26)13(8-23)18(22)20(12)27/h6,8-9,11,14,28H,3-5,7,22H2,1-2H3,(H,24,25)/t11-,14-/m0/s1',
            'inchi_key': 'NPGKFFQPHSMESG-FZMZJTMJSA-N',
            'isopen': False, 
            'iupacName': '',
            'language': 'english',
            'license_id': 'CC BY-NC 4.0 Deed',
            'license_title': 'Attribution-NonCommercial 4.0 International',
            'license_url': 'https://creativecommons.org/licenses/by-nc/4.0/legalcode',
            'maintainer': '',
            'maintainer_email': None, 
            'measurement_technique': 'heteronuclear single quantum coherence',
            'measurement_technique_iri': 'CHMO:0000604',
            'metadata_created': '2025-02-03T14:35:36.229612',
            'metadata_modified': '2025-03-07T09:58:42.738120',
            'mol_formula': '',
            'name': 'actinoquinonal_a_nmr_data-hsqc',
            'notes': 'This dataset contains NMR spectra obtained for the sample -actinoquinonal_A_NMR_Data date: 2021-10-02T04:26:18.000Z isFt: true name: actinoquinonal_A_NMR_Data/0 phc0: 0,0 phc1: 0,0 type: NMR Spectrum DECIM: 16 aqMod: 3 isFid: false tdOff: 0,0 title: Parameter file, TOPSPIN\t\tVersion 2.1 DSPFVS: 12 nucleus: 1H,1H reverse: false,false solvent: CDCl3 dimension: 2 increment: 10.01513082882905 isComplex: false probeName: 5 mm TXI D/1H-13C/15N XYZ-GRD Z8323/141 experiment: cosy groupDelay: -1 temperature: 298 spectrumSize: 1024,1024 baseFrequency: 600.05,600.05 fieldStrength: 14.093131413328843 numberOfScans: 256 pulseSequence: cosygpqf spectralWidth: 20.0302616576581,20 numberOfPoints: 3 relaxationTime: 1.5 acquisitionTime: 0.0000832000000000001 frequencyOffset: 3607.619024023734,3607.619024023734 originFrequency: 600.053607619024,600.053607619024 pulseStrength90: 25000 experimentNumber: 0 acquisitionScheme: notPhaseSensitive linearPredictionBin: 0,256 lpNumberOfCoefficients: 0,32 windowMultiplicationMode: 3,3 date: 2021-10-03T09:12:33.000Z isFt: true name: actinoquinonal_A_NMR_Data/0 phc0: 0,0 phc1: 0,0 type: NMR Spectrum DECIM: 16 aqMod: 3 isFid: false tdOff: 0,0 title: Parameter file, TOPSPIN\t\tVersion 2.1 DSPFVS: 12 nucleus: 1H,13C reverse: false,false solvent: CDCl3 dimension: 2 increment: 0.41729699776872503 isComplex: false probeName: 5 mm TXI D/1H-13C/15N XYZ-GRD Z8323/141 experiment: hmbc groupDelay: -1 temperature: 298 spectrumSize: 2048,1024 baseFrequency: 600.05,150.882693 fieldStrength: 14.093131413328843 numberOfScans: 256 pulseSequence: hmbcgplpndqf spectralWidth: 20.0302558928988,222.095059442626 numberOfPoints: 49 relaxationTime: 1.5 acquisitionTime: 0.0019968000000000013 frequencyOffset: 3780.3160000748903,16597.096230015042 originFrequency: 600.053780316,150.89929009623 pulseStrength90: 25000 experimentNumber: 0 acquisitionScheme: notPhaseSensitive linearPredictionBin: 0,256 lpNumberOfCoefficients: 0,32 windowMultiplicationMode: 3,3 date: 2021-10-02T18:55:08.000Z isFt: true name: actinoquinonal_A_NMR_Data/0 phc0: -65.8161,0 phc1: 0,0 type: NMR Spectrum DECIM: 16 aqMod: 3 isFid: false tdOff: 0,0 title: Parameter file, TOPSPIN\t\tVersion 2.1 DSPFVS: 12 nucleus: 1H,13C reverse: false,false solvent: CDCl3 dimension: 2 increment: 5.007565475493225 isComplex: false probeName: 5 mm TXI D/1H-13C/15N XYZ-GRD Z8323/141 experiment: hsqc groupDelay: -1 temperature: 298 spectrumSize: 1024,1024 baseFrequency: 600.05,150.882693 fieldStrength: 14.093131413328843 numberOfScans: 128 pulseSequence: hsqcetgpsi2 spectralWidth: 20.0302619019729,220 numberOfPoints: 5 relaxationTime: 1.5 acquisitionTime: 0.00016640000000000006 frequencyOffset: 3600.300000016432,16597.096230015042 originFrequency: 600.0536003,150.89929009623 pulseStrength90: 25000 experimentNumber: 0 acquisitionScheme: Echo-antiecho linearPredictionBin: 0,512 lpNumberOfCoefficients: 0,32 windowMultiplicationMode: 4,4 date: 2021-12-23T09:41:36.000Z isFt: true name: actinoquinonal_A_NMR_Data/0 phc0: -162.15,90 phc1: 0,-180 type: NMR Spectrum DECIM: 16 aqMod: 3 isFid: false tdOff: 0,0 title: Parameter file, TOPSPIN\t\tVersion 2.1 DSPFVS: 12 nucleus: 1H,1H reverse: false,false solvent: CDCl3 dimension: 2 increment: 4.00605238039458 isComplex: false probeName: 5 mm TXI D/1H-13C/15N XYZ-GRD Z8323/141 experiment: noesy groupDelay: -1 temperature: 298 spectrumSize: 1024,1024 baseFrequency: 600.05,600.05 fieldStrength: 14.093131413328843 numberOfScans: 64 pulseSequence: noesyphpp spectralWidth: 20.0302619019729,20 numberOfPoints: 6 relaxationTime: 2 acquisitionTime: 0.0002080000000000001 frequencyOffset: 3600.300000016432,3600.300000016432 originFrequency: 600.0536003,600.0536003 pulseStrength90: 25000 experimentNumber: 0 acquisitionScheme: States-TPPI linearPredictionBin: 0,0 lpNumberOfCoefficients: 0,0 windowMultiplicationMode: 4,4 date: {"year":2021,"month":10,"day":23} isFt: true name: actinoquinonal_A_13C.jdf type: NMR SPECTRUM isFid: false title: title: Parameter file, TOPSPIN\t\tVersion 2.1 / comment: Parameter file, TOPSPIN\t\tVersion 2.1 / author:nmr / site: author: nmr nucleus: 13C solvent: CHLOROFORM-D metadata: [object Object] dimension: 1 isComplex: true probeName: null experiment: 1d temperature: 298 baseFrequency: 150.91875159839753 fieldStrength: 14.093496686836302 numberOfScans: 25600 pulseSequence: zgpg30 spectralWidth: null numberOfPoints: 32768 relaxationTime: NA acquisitionMode: 0 acquisitionTime: NA frequencyOffset: null originFrequency: null pulseStrength90: null spectralWidthClipped: null date: {"year":2021,"month":5,"day":13} isFt: false name: actinoquinonal_A_1H.jdf type: NMR SPECTRUM isFid: true title: title: 210515 1 / comment: single_pulse / author:delta / site: JNM-ECS400 author: delta nucleus: 1H solvent: CHLOROFORM-D metadata: [object Object] dimension: 1 isComplex: true probeName: 2772 experiment: 1d sampleName: 2105151 temperature: 292.54999999999995 baseFrequency: 399.79256015247455 digitalFilter: 19.686298370361328 fieldStrength: 9.389766 numberOfScans: 16 pulseSequence: proton.jxp spectralWidth: 23.75913755462968 numberOfPoints: 16384 relaxationTime: 5 acquisitionMode: 0 acquisitionTime: 1.7249075200000001 frequencyOffset: 1998.9628007623728 originFrequency: 399.78219837825003 pulseStrength90: 39682.53968253968 spectralWidthClipped: 19006817.414588254',
            'num_resources': 1, 
            'num_tags': 1, 
            'organization': {'id': '0170ebc4-b55a-47a9-96b2-9981cef2ac7e',
                             'name': 'nhs-wirral-ccg',
                             'title': 'NHS Wirral CCG',
                             'type': 'repository',
                             'description': '',
                             'image_url': '',
                             'created': '2021-11-22T10:59:13.904545',
                             'is_organization': True, 
                             'approval_status': 'approved',
                             'state': 'active'}, 
            'owner_org': '0170ebc4-b55a-47a9-96b2-9981cef2ac7e',
            'private': False, 
            'related_molecule': [], 
            'smiles': 'CC(C)CC[C@@H]1O[C@H](CC(=O)O)CC2=CC3=C(C(=O)C(C=O)=C(N)C3=O)C(O)=C21',
            'state': 'active',
            'title': 'actinoquinonal_A_NMR_Data.hsqc',
            'type': 'dataset',
            'url': 'https://nmrxiv.org/D3596',
            'version': '',
            'extras': [
                {'key': 'license_url',
                 'value': 'https://creativecommons.org/licenses/by-nc/4.0/legalcode'}, 
                {'key': 'harvest_object_id',
                 'value': '287f82dc-5804-438d-b2e2-798e43cbf517'}, 
                {'key': 'harvest_source_id',
                 'value': 'b11775da-a6bc-45c1-bb4c-f71a5890d34b'}, 
                {'key': 'harvest_source_title',
                 'value': 'nmrXiv'}
            ], 
            'resources': [
                {'cache_last_updated': None, 
                 'cache_url': None, 
                 'created': '2025-02-03T14:35:36.232125',
                 'format': 'HTML',
                 'hash': '',
                 'id': '2c48d6cc-2af2-4448-a8f8-90881a49c6d1',
                 'last_modified': None, 
                 'metadata_modified': '2025-02-03T14:35:36.225126',
                 'mimetype': None, 
                 'mimetype_inner': None, 
                 'name': 'actinoquinonal_A_NMR_Data.hsqc',
                 'package_id': 'nmrxiv-d3596',
                 'position': 0, 
                 'resource_type': 'HTML',
                 'size': None, 
                 'state': 'active',
                 'url': 'https://nmrxiv.org/D3596',
                 'url_type': None, 
                 'tracking_summary': {'total': 0, 'recent': 0}, 
                 'has_views': False}
            ], 
            'tags': [
                {'display_name': 'heteronuclear-single-quantum-coherence',
                 'id': 'f769ca74-abeb-472d-a347-15d945c46e11',
                 'name': 'heteronuclear-single-quantum-coherence',
                 'state': 'active',
                 'vocabulary_id': None}
            ], 
            'variableMeasured': [
                {'variableMeasured_name': 'NMR solvent',
                 'variableMeasured_propertyID': 'NMR:1000330',
                 'variableMeasured_tsurl': '',
                 'variableMeasured_value': 'CDCl3'}, 
                {'variableMeasured_name': 'acquisition nucleus',
                 'variableMeasured_propertyID': 'NMR:1400083',
                 'variableMeasured_tsurl': '',
                 'variableMeasured_value': "['1H','13C']"}, 
                {'variableMeasured_name': 'number of data points',
                 'variableMeasured_propertyID': 'NMR:1000176',
                 'variableMeasured_tsurl': '',
                 'variableMeasured_value': '5'}, 
                {'variableMeasured_name': 'relaxation time measurement',
                 'variableMeasured_propertyID': 'FIX:0000202',
                 'variableMeasured_tsurl': 'http://purl.obolibrary.org/obo/FIX_0000202',
                 'variableMeasured_value': '1.5'}, 
                {'variableMeasured_name': 'NMR spectrum by dimensionality',
                 'variableMeasured_propertyID': 'NMR:1000117',
                 'variableMeasured_tsurl': '',
                 'variableMeasured_value': '2'}, 
                {'variableMeasured_name': 'NMR probe',
                 'variableMeasured_propertyID': 'OBI:0000516',
                 'variableMeasured_tsurl': 'http://purl.obolibrary.org/obo/OBI_0000516',
                 'variableMeasured_value': '5 mm TXI D/1H-13C/15N XYZ-GRD Z8323/141'}, 
                {'variableMeasured_name': 'Temperature',
                 'variableMeasured_propertyID': 'NCIT:C25206',
                 'variableMeasured_tsurl': 'http://purl.obolibrary.org/obo/NCIT_C25206',
                 'variableMeasured_value': '298'}, 
                {'variableMeasured_name': 'irradiation frequency',
                 'variableMeasured_propertyID': 'NMR:1400026',
                 'variableMeasured_tsurl': '',
                 'variableMeasured_value': '[600.05, 150.882693]'},
                {'variableMeasured_name': 'magnetic field strength',
                 'variableMeasured_propertyID': 'MR:1400253',
                 'variableMeasured_tsurl': '',
                 'variableMeasured_value': '14.093131413328843'}, 
                {'variableMeasured_name': 'number of scans',
                 'variableMeasured_propertyID': 'NMR:1400087',
                 'variableMeasured_tsurl': '',
                 'variableMeasured_value': '128'}, 
                {'variableMeasured_name': 'nuclear magnetic resonance pulse sequence',
                 'variableMeasured_propertyID': 'CHMO:0001841',
                 'variableMeasured_tsurl': 'http://purl.obolibrary.org/obo/CHMO_0001841',
                 'variableMeasured_value': 'hsqcetgpsi2'}, 
                {'variableMeasured_name': 'Spectral Width',
                 'variableMeasured_propertyID': 'NCIT:C156496',
                 'variableMeasured_tsurl': 'http://purl.obolibrary.org/obo/NCIT_C156496',
                 'variableMeasured_value': '[20.0302619019729, 220]'}
            ]
        }

        dataset = AnalysisDataset()
        
        # Define Dataset
        if dataset_dict.get('doi'):
            dataset.id = 'https://doi.org/' + dataset_dict.get('doi')
            dataset.identifier = 'https://doi.org/'+ dataset_dict.get('doi')
        else:
            dataset.id = dataset_dict.get('id').strip()
            dataset.identifier = dataset_dict.get('id').strip()
            
        dataset.title.append(dataset_dict.get('title'))
        dataset.description.append(dataset_dict.get('notes'))
        if dataset_dict.get('language'):
            dataset.language.append(LinguisticSystem(dataset_dict.get('language')))
            
        if dataset_dict.get('url'):
            dataset.landing_page = Document(dataset_dict.get('url'))

        dataset.release_date = dataset_dict.get('metadata_created')
        dataset.modification_date = dataset_dict.get('metadata_modified')

        contexts= {
            "comments": {
                "description": "Auto generated by LinkML jsonld context generator",
                "generation_date": "2025-03-14T11:57:46",
                "source": "dcat_4c_ap.yaml"
            },
            "@context": {
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "BFO": {
                    "@id": "http://purl.obolibrary.org/obo/BFO_",
                    "@prefix": 'true'
                },
                "CHEBI": {
                    "@id": "http://purl.obolibrary.org/obo/CHEBI_",
                    "@prefix": 'true'
                },
                "CHEMINF": {
                    "@id": "http://semanticscience.org/resource/CHEMINF_",
                    "@prefix": 'true'
                },
                "CHMO": {
                    "@id": "http://purl.obolibrary.org/obo/CHMO_",
                    "@prefix": 'true'
                },
                "FOODON": {
                    "@id": "http://purl.obolibrary.org/obo/FOODON_",
                    "@prefix": 'true'
                },
                "IAO": {
                    "@id": "http://purl.obolibrary.org/obo/IAO_",
                    "@prefix": 'true'
                },
                "NCIT": {
                    "@id": "http://purl.obolibrary.org/obo/NCIT_",
                    "@prefix": 'true'
                },
                "NMR": "http://nmrML.org/nmrCV#NMR:",
                "OBI": {
                    "@id": "http://purl.obolibrary.org/obo/OBI_",
                    "@prefix": 'true'
                },
                "PATO": {
                    "@id": "http://purl.obolibrary.org/obo/PATO_",
                    "@prefix": 'true'
                },
                "RO": {
                    "@id": "http://purl.obolibrary.org/obo/RO_",
                    "@prefix": 'true'
                },
                "RXNO": {
                    "@id": "http://purl.obolibrary.org/obo/RXNO_",
                    "@prefix": 'true'
                },
                "SIO": {
                    "@id": "http://semanticscience.org/resource/SIO_",
                    "@prefix": 'true'
                },
                "T4FS": {
                    "@id": "http://purl.obolibrary.org/obo/T4FS_",
                    "@prefix": 'true'
                },
                "adms": "http://www.w3.org/ns/adms#",
                "biolink": "https://w3id.org/biolink/vocab/",
                "dcat": "http://www.w3.org/ns/dcat#",
                "dcatap": "http://data.europa.eu/r5r/",
                "dcterms": "http://purl.org/dc/terms/",
                "doi": "https://doi.org/",
                "eli": "http://data.europa.eu/eli/ontology#",
                "ex": "http://example.org/",
                "foaf": "http://xmlns.com/foaf/0.1/",
                "linkml": "https://w3id.org/linkml/",
                "linkmldcatap": "https://stroemphi.github.io/dcat-4C-ap/dcat_ap_linkml/",
                "locn": "http://www.w3.org/ns/locn#",
                "nfdi": "https://stroemphi.github.io/dcat-4C-ap/dcat_4nfdi_ap/",
                "nfdi4c": "https://stroemphi.github.io/dcat-4C-ap/dcat_4c_ap/",
                "odrl": "http://www.w3.org/ns/odrl/2/",
                "owl": "http://www.w3.org/2002/07/owl#",
                "prov": "http://www.w3.org/ns/prov#",
                "qudt": "http://qudt.org/schema/qudt/",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "schema": "http://schema.org/",
                "skos": "http://www.w3.org/2004/02/skos/core#",
                "sosa": "http://www.w3.org/ns/sosa/",
                "spdx": "http://spdx.org/rdf/terms#",
                "time": "http://www.w3.org/2006/time#",
                "vcard": "http://www.w3.org/2006/vcard/ns#",
                "@vocab": "https://stroemphi.github.io/dcat-4C-ap/dcat_4c_ap/",
                "access_rights": {
                    "@id": "dcterms:accessRights"
                },
                "access_service": {
                    "@id": "dcat:accessService"
                },
                "access_URL": {
                    "@id": "dcat:accessURL"
                },
                "algorithm": {
                    "@id": "spdx:algorithm"
                },
                "applicable_legislation": {
                    "@id": "dcatap:applicableLegislation"
                },
                "application_profile": {
                    "@id": "dcterms:conformsTo"
                },
                "availability": {
                    "@id": "dcatap:availability"
                },
                "bbox": {
                    "@id": "dcat:bbox"
                },
                "beginning": {
                    "@id": "time:hasBeginning"
                },
                "byte_size": {
                    "@id": "dcat:byteSize"
                },
                "catalogue": {
                    "@id": "dcat:catalog"
                },
                "centroid": {
                    "@id": "dcat:centroid"
                },
                "change_type": {
                    "@id": "adms:status"
                },
                "checksum": {
                    "@id": "spdx:checksum"
                },
                "checksum_value": {
                    "@id": "spdx:checksumValue"
                },
                "inchi": {
                    "@type": "CHEMINF:000113",
                    "@id": "inchi"
                },
                "inchikey": {
                    "@type": "CHEMINF:000059",
                    "@id": "inchikey"
                },
                "iupac_formula": {
                    "@type": "CHEMINF:000037",
                    "@id": "iupac_formula"
                },
                "smiles": {
                    "@type": "CHEMINF:000018",
                    "@id": "smiles"
                },
                "composed_of": {
                    "@type": "CHEBI:23367",
                    "@id": "composed_of"
                },
                "compression_format": {
                    "@id": "dcat:compressFormat"
                },
                "conforms_to": {
                    "@id": "dcterms:conformsTo"
                },
                "contact_point": {
                    "@id": "dcat:contactPoint"
                },
                "creator": {
                    "@id": "dcterms:creator"
                },
                "dataset_distribution": {
                    "@id": "dcat:distribution"
                },
                "from_CV": {
                    "@type": "xsd:anyURI",
                    "@id": "schema:inDefinedTermSet"
                },
                "describes_activity": {
                    "@type": "prov:Activity",
                    "@id": "dcterms:relation"
                },
                "describes_entity": {
                    "@type": "prov:Entity",
                    "@id": "dcterms:relation"
                },
                "description": {
                    "@id": "dcterms:description"
                },
                "documentation": {
                    "@id": "foaf:page"
                },
                "download_URL": {
                    "@id": "dcat:downloadURL"
                },
                "end": {
                    "@id": "time:hasEnd"
                },
                "end_date": {
                    "@id": "dcat:endDate"
                },
                "endpoint_description": {
                    "@id": "dcat:endpointDescription"
                },
                "endpoint_URL": {
                    "@id": "dcat:endpointURL"
                },
                "evaluated_activity": {
                    "@type": "prov:Activity",
                    "@id": "prov:wasInformedBy"
                },
                "evaluated_entity": {
                    "@type": "prov:Entity",
                    "@id": "prov:used"
                },
                "format": {
                    "@id": "dcterms:format"
                },
                "frequency": {
                    "@id": "dcterms:accrualPeriodicity"
                },
                "geographical_coverage": {
                    "@id": "dcterms:spatial"
                },
                "geometry": {
                    "@id": "locn:geometry"
                },
                "had_role": {
                    "@id": "dcat:hadRole"
                },
                "has_dataset": {
                    "@id": "dcat:dataset"
                },
                "has_part": {
                    "@id": "dcterms:hasPart"
                },
                "has_policy": {
                    "@id": "odrl:hasPolicy"
                },
                "has_qualitative_attribute": {
                    "@type": "prov:Entity",
                    "@id": "dcterms:relation"
                },
                "has_quantitative_attribute": {
                    "@type": "qudt:Quantity",
                    "@id": "dcterms:relation"
                },
                "has_role": {
                    "@id": "has_role"
                },
                "has_version": {
                    "@id": "dcat:hasVersion"
                },
                "homepage": {
                    "@id": "foaf:homepage"
                },
                "id": "@id",
                "identifier": {
                    "@id": "dcterms:identifier"
                },
                "in_series": {
                    "@id": "dcat:inSeries"
                },
                "is_referenced_by": {
                    "@id": "dcterms:isReferencedBy"
                },
                "keyword": {
                    "@id": "dcat:keyword"
                },
                "landing_page": {
                    "@id": "dcat:landingPage"
                },
                "language": {
                    "@id": "dcterms:language"
                },
                "licence": {
                    "@id": "dcterms:license"
                },
                "linked_schemas": {
                    "@id": "dcterms:conformsTo"
                },
                "listing_date": {
                    "@id": "dcterms:issued"
                },
                "media_type": {
                    "@id": "dcat:mediaType"
                },
                "modification_date": {
                    "@id": "dcterms:modified"
                },
                "name": {
                    "@id": "foaf:name"
                },
                "notation": {
                    "@id": "skos:notation"
                },
                "occurred_in": {
                    "@type": "prov:Entity",
                    "@id": "BFO:0000066"
                },
                "other_identifier": {
                    "@id": "adms:identifier"
                },
                "packaging_format": {
                    "@id": "dcat:packageFormat"
                },
                "preferred_label": {
                    "@id": "skos:prefLabel"
                },
                "primary_topic": {
                    "@id": "foaf:primaryTopic"
                },
                "provenance": {
                    "@id": "dcterms:provenance"
                },
                "publisher": {
                    "@id": "dcterms:publisher"
                },
                "qualified_attribution": {
                    "@id": "prov:qualifiedAttribution"
                },
                "qualified_relation": {
                    "@id": "dcat:qualifiedRelation"
                },
                "has_quantity_type": {
                    "@type": "@id",
                    "@id": "qudt:hasQuantityKind"
                },
                "unit": {
                    "@type": "@id",
                    "@id": "qudt:unit"
                },
                "rdf_type": {
                    "@type": "schema:DefinedTerm",
                    "@id": "rdf:type"
                },
                "realized_plan": {
                    "@type": "prov:Entity",
                    "@id": "prov:used"
                },
                "record": {
                    "@id": "dcat:record"
                },
                "related_resource": {
                    "@id": "dcterms:relation"
                },
                "relation": {
                    "@id": "dcterms:relation"
                },
                "release_date": {
                    "@id": "dcterms:issued"
                },
                "rights": {
                    "@id": "dcterms:rights"
                },
                "sample": {
                    "@id": "adms:sample"
                },
                "serves_dataset": {
                    "@id": "dcat:servesDataset"
                },
                "service": {
                    "@id": "dcat:service"
                },
                "source": {
                    "@id": "dcterms:source"
                },
                "source_metadata": {
                    "@id": "dcterms:source"
                },
                "spatial_resolution": {
                    "@id": "dcat:spatialResolutionInMeters"
                },
                "start_date": {
                    "@id": "dcat:startDate"
                },
                "status": {
                    "@id": "adms:status"
                },
                "temporal_coverage": {
                    "@id": "dcterms:temporal"
                },
                "temporal_resolution": {
                    "@id": "dcat:temporalResolution"
                },
                "theme": {
                    "@id": "dcat:theme"
                },
                "themes": {
                    "@id": "dcat:themeTaxonomy"
                },
                "title": {
                    "@id": "dcterms:title"
                },
                "type": {
                    "@id": "dcterms:type"
                },
                "used_tool": {
                    "@type": "prov:Entity",
                    "@id": "prov:used"
                },
                "value": {
                    "@id": "prov:value"
                },
                "version": {
                    "@id": "dcat:version"
                },
                "version_notes": {
                    "@id": "adms:versionNotes"
                },
                "was_generated_by": {
                    "@id": "prov:wasGeneratedBy"
                },
                "Activity": {
                    "@id": "prov:Activity"
                },
                "Agent": {
                    "@id": "foaf:Agent"
                },
                "AnalysisDataset": {
                    "@id": "dcat:Dataset"
                },
                "AnalysisSourceData": {
                    "@id": "prov:Entity"
                },
                "Attribution": {
                    "@id": "prov:Attribution"
                },
                "Catalogue": {
                    "@id": "dcat:Catalog"
                },
                "CataloguedResource": {
                    "@id": "dcat:Resource"
                },
                "CatalogueRecord": {
                    "@id": "dcat:CatalogRecord"
                },
                "Checksum": {
                    "@id": "spdx:Checksum"
                },
                "ChecksumAlgorithm": {
                    "@id": "spdx:ChecksumAlgorithm"
                },
                "ChemicalEntity": {
                    "@id": "CHEBI:23367"
                },
                "ChemicalReaction": {
                    "@id": "RXNO:0000329"
                },
                "ChemicalSample": {
                    "@id": "ChemicalSample"
                },
                "ChemicalSubstance": {
                    "@id": "prov:Entity"
                },
                "ClassifierMixin": {
                    "@id": "nfdi:ClassifierMixin"
                },
                "Concept": {
                    "@id": "skos:Concept"
                },
                "ConceptScheme": {
                    "@id": "skos:ConceptScheme"
                },
                "DataAnalysis": {
                    "@id": "prov:Activity"
                },
                "DataCreatingActivity": {
                    "@id": "prov:Activity"
                },
                "DataService": {
                    "@id": "dcat:DataService"
                },
                "Dataset": {
                    "@id": "dcat:Dataset"
                },
                "DatasetSeries": {
                    "@id": "dcat:DatasetSeries"
                },
                "DefinedTerm": {
                    "@id": "schema:DefinedTerm"
                },
                "Distribution": {
                    "@id": "dcat:Distribution"
                },
                "Document": {
                    "@id": "foaf:Document"
                },
                "Environment": {
                    "@id": "prov:Entity"
                },
                "EvaluatedActivity": {
                    "@id": "prov:Activity"
                },
                "EvaluatedEntity": {
                    "@id": "prov:Entity"
                },
                "Frequency": {
                    "@id": "dcterms:Frequency"
                },
                "Geometry": {
                    "@id": "locn:Geometry"
                },
                "HardwareTool": {
                    "@id": "nfdi:HardwareTool"
                },
                "Identifier": {
                    "@id": "adms:Identifier"
                },
                "InChi": {
                    "@id": "CHEMINF:000113"
                },
                "InChIKey": {
                    "@id": "CHEMINF:000059"
                },
                "IUPACChemicalFormula": {
                    "@id": "CHEMINF:000037"
                },
                "Kind": {
                    "@id": "vcard:Kind"
                },
                "Laboratory": {
                    "@id": "prov:Entity"
                },
                "LegalResource": {
                    "@id": "eli:LegalResource"
                },
                "LicenseDocument": {
                    "@id": "dcterms:LicenseDocument"
                },
                "LinguisticSystem": {
                    "@id": "dcterms:LinguisticSystem"
                },
                "Location": {
                    "@id": "dcterms:Location"
                },
                "MediaType": {
                    "@id": "dcterms:MediaType"
                },
                "MediaTypeOrExtent": {
                    "@id": "dcterms:MediaTypeOrExtent"
                },
                "NMRAnalysisDataset": {
                    "@id": "dcat:Dataset"
                },
                "NMRSpectralAnalysis": {
                    "@id": "NMR:1000259"
                },
                "NMRSpectroscopy": {
                    "@id": "NMRSpectroscopy"
                },
                "NMRSpectrum": {
                    "@id": "NMR:1002007"
                },
                "PeriodOfTime": {
                    "@id": "dcterms:PeriodOfTime"
                },
                "Plan": {
                    "@id": "prov:Entity"
                },
                "Policy": {
                    "@id": "odrl:Policy"
                },
                "ProvenanceStatement": {
                    "@id": "dcterms:ProvenanceStatement"
                },
                "QualitativeAttribute": {
                    "@id": "prov:Entity"
                },
                "QuantitativeAttribute": {
                    "@id": "qudt:Quantity"
                },
                "Relationship": {
                    "@id": "dcat:Relationship"
                },
                "ResearchCatalog": {
                    "@id": "dcat:Catalog"
                },
                "ResearchDataset": {
                    "@id": "dcat:Dataset"
                },
                "Resource": {
                    "@id": "rdfs:Resource"
                },
                "RightsStatement": {
                    "@id": "dcterms:RightsStatement"
                },
                "Role": {
                    "@id": "dcat:Role"
                },
                "SMILES": {
                    "@id": "CHEMINF:000018"
                },
                "SoftwareTool": {
                    "@id": "nfdi:SoftwareTool"
                },
                "Standard": {
                    "@id": "dcterms:Standard"
                },
                "SupportiveEntity": {
                    "@id": "linkmldcatap:SupportiveEntity"
                },
                "TimeInstant": {
                    "@id": "time:Instant"
                },
                "Tool": {
                    "@id": "prov:Entity"
                }
            }
        }
        g.as_rdf_graph(dataset, contexts=contexts)
        return g
"""
        # Author Information
        contact_node = BNode()
        g.add((dataset_uri, DCAT.contactPoint, contact_node))
        g.add((contact_node, RDF.type, VCARD.Kind))
        g.add((contact_node, VCARD.fn, Literal(dataset_dict.get('author'))))

        # Dataset Theme
        theme_node = BNode()
        g.add((dataset_uri, DCAT.theme, theme_node))
        g.add((theme_node, RDF.type, SKOS.Concept))
        if dataset_dict.get('keyword') is not None:
            g.add((theme_node, SKOS.prefLabel, Literal(dataset_dict.get('keyword'))))

        # wasGeneratedBy Activity
        was_generated_by = BNode()
        g.add((dataset_uri, PROV.wasGeneratedBy, was_generated_by))
        g.add((was_generated_by, RDF.type, CHMO['0000595']))
        g.add((was_generated_by, RDF.type, PROV.Activity))

        # Used Chemical Entity Node (CHEBI)
        used_entity_chem = BNode()
        g.add((was_generated_by, PROV.used, used_entity_chem))
        g.add((used_entity_chem, RDF.type, CHEBI['59999']))
        g.add((used_entity_chem, DCT.identifier, Literal(dataset_dict.get('doi'))))
        g.add((used_entity_chem, DCT.title, Literal(dataset_dict.get('title'))))
        g.add((used_entity_chem, CHEMINF['000059'], Literal(dataset_dict.get('inchi_key'))))  # inchi_key
        g.add((used_entity_chem, CHEMINF['000113'], Literal(dataset_dict.get('inchi'))))  # inchi
        g.add((used_entity_chem, CHEMINF['000018'], Literal(dataset_dict.get('smiles'))))  # smiles
        g.add((used_entity_chem, CHEMINF['000037'], Literal(dataset_dict.get('mol_formula'))))  # mol_formula


        # Used Instrument Entity Node (NMR Instrument)
        used_tool = BNode()
        g.add((was_generated_by, PROV.used, used_tool))
        g.add((used_tool, RDF.type, OBI['0000566']))
        g.add((used_tool,RDF.type, PROV.Entity))

        variable_node = BNode()
        g.add((used_tool, PROV.used, variable_node))

        # Variable Measured
        if dataset_dict.get('variableMeasured',[]):
            variable_measured = dataset_dict.get('variableMeasured', [])

            for vm in variable_measured:
                property_id = vm['variableMeasured_propertyID']
                value = vm['variableMeasured_value']
                variable_name = vm['variableMeasured_name']

                # Split to get namespace
                if ':' in property_id:
                    prefix, identifier = property_id.split(':', 1)
                else:
                    # Handle the case where it's not in the expected format
                    prefix = None
                    identifier = property_id  # or raise an error/log warning

                if prefix == 'NMR':
                    prop_uri = URIRef(NMR['1000330'])
                elif prefix == 'NCIT':
                    prop_uri = URIRef(NCIT[identifier])
                elif prefix == 'FIX':
                    prop_uri = URIRef(FIX[identifier])
                elif prefix == 'CHMO':
                    prop_uri = URIRef(CHMO[identifier])
                elif prefix == 'OBI':
                    prop_uri = URIRef(OBI[identifier])
                else:
                    prop_uri= URIRef(IAO['0000140'])  # Skip unrecognized prefixes

                # Add title before the property
                # if property_id in property_title_map:
                used_entity = BNode()
                g.add((variable_node, DCT.relation, used_entity))

                if variable_name == 'Temperature':
                    g.add((used_entity, RDF.type, QUDT.Quantity))  # Temperature
                    g.add((used_entity, QUDT.hasQuantityKind, URIRef("http://qudt.org/vocab/quantitykind/Temperature")))
                    g.add((used_entity, QUDT.unit, URIRef("https://qudt.org/vocab/unit/K")))
                    g.add((used_entity, QUDT.value, Literal(value)))
                else:
                    g.add((used_entity, RDF.type, PROV.Entity))
                    g.add((used_entity, RDF.type, prop_uri))
                    g.add((used_entity, DCT.title, Literal(variable_name)))
                    g.add((used_entity, PROV.value, Literal(value)))# Create a blank node for Quantity

        return g
"""


    