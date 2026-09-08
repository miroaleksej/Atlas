from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source.lawspace.pharmaceutical_problem_atlas import PharmaceuticalResearchOperatorOwner

SOURCE_SHA256 = "869f3256fdd8059a3b0d0a40ea84e69927f2548d8a16dc8c14a9db565dab4490"
SOURCE_NAME = "Сборник 24.05.24.pdf"
SCHEMA_VERSION = "v8.3"

# TOC transcription fixes only. They correct parser ambiguity and perform no
# scientific interpretation.
TITLE_OVERRIDES = {
    167: "СРАВНИТЕЛЬНЫЙ АНАЛИЗ СОДЕРЖАНИЯ НОРМИРОВАННЫХ ТЯЖЕЛЫХ МЕТАЛЛОВ В СЫРЬЕ SANGUISORBA OFFICINALIS L. НА ТЕРРИТОРИИ С РАЗЛИЧНОЙ АНТРОПОГЕННОЙ НАГРУЗКОЙ",
    171: "РАЗРАБОТКА И СТАНДАРТИЗАЦИЯ ЛЕКАРСТВЕННОЙ ФОРМЫ НА ОСНОВЕ ФЛАВОНОИДНОЙ ФРАКЦИИ ЭРУКИ ПОСЕВНОЙ (ERUCA SATIVA) СЕМ. КАПУСТНЫЕ (BRASSICACEAE)",
    180: "ЗОЛЬНОСТЬ, КАК ЭКОЛОГИЧЕСКИЙ ПОКАЗАТЕЛЬ ЧИСТОТЫ СЫРЬЯ BETULA PUBESCENS EHRH., НА ТЕРРИТОРИИ С РАЗЛИЧНОЙ АНТРОПОГЕННОЙ НАГРУЗКОЙ",
    197: "ВОЗМОЖНОСТИ ИСПОЛЬЗОВАНИЯ НОВЫХ ПРОИЗВОДНЫХ ЦИАНОТИОАЦЕТАМИДА В КАЧЕСТВЕ ТИМОАНАЛЕПТИЧЕСКИХ СРЕДСТВ. РАНДОМИЗИРОВАННОЕ КОНТРОЛИРУЕМОЕ ИССЛЕДОВАНИЕ",
    230: "ПИЩЕВЫЕ СИСТЕМЫ АНТИОКСИДАНТНОЙ НАПРАВЛЕННОСТИ: СПЕЦИАЛИЗИРОВАННЫЕ ПРОДУКТЫ В ФОРМЕ БАД. НАТУРНЫЕ ИССЛЕДОВАНИЯ ЭФФЕКТИВНОСТИ",
    237: "ЭФФЕКТИВНОСТЬ ПРИМЕНЕНИЯ ГИДРОГЕНИЗИРОВАННОГО КАСТОРОВОГО МАСЛА В КАЧЕСТВЕ СОЛЮБИЛИЗАТОРА ДЛЯ ПОЛУЧЕНИЯ МОДЕЛЬНЫХ РАСТВОРОВ ТРУДНОРАСТВОРИМОГО СОЕДИНЕНИЯ – ПРОИЗВОДНОГО 3-ГИДРОКСИХИНАЗОЛИНА",
    240: "ИЗУЧЕНИЕ ВЛИЯНИЯ ОБЪЕМНОЙ ДОЛИ СОЛЕВОГО РАСТВОРА V2 НА РОСТ БАКТЕРИИ VIBRIO NATRIEGENS",
}

# Deep cards retain human-curated scientific context.  They no longer bypass the
# semantic operator adjudicator: research_operator is selected from the typed
# problem graph, while these rows contribute explicit problem type, axes, blockers
# and candidate-region context already justified in v8.2.
DEEP_CONTEXT: dict[int, dict[str, Any]] = {
    117: {
        "problem_type": "FORMULATION_PROPERTY_TRADEOFF",
        "relevant_axes": ["chelate_speciation", "diffusive_bioavailability", "formulation", "safety_pharmacology", "assay_reproducibility"],
        "blocking_uncertainties": ["IN_VIVO_TOPICAL_EXPOSURE_NOT_ESTABLISHED", "FULL_TOXICOLOGY_NOT_ESTABLISHED"],
        "candidate_seed": {"search_region": "zinc-chelate × ointment composition", "claim": "FORMULATION_OPTIMIZATION_REGION_ONLY"},
    },
    131: {
        "problem_type": "MULTIOBJECTIVE_MEDCHEM_GAP",
        "relevant_axes": ["molecular_target", "potency_metric", "selectivity", "selectivity_profile", "off_target_liability", "safety_pharmacology", "synthetic_accessibility", "solubility"],
        "blocking_uncertainties": ["QSAR_APPLICABILITY_DOMAIN_REQUIRED", "ORTHOGONAL_EXPERIMENTAL_VALIDATION_REQUIRED", "SELECTIVITY_PANEL_REQUIRED"],
        "candidate_seed": {"target": "HDAC6", "search_region": "verified-structure activity/selectivity/safety Pareto region", "claim": "NO_NEW_MOLECULE_ASSERTED"},
    },
    193: {
        "problem_type": "EVIDENCE_GAP",
        "relevant_axes": ["indication", "target_population", "clinical_endpoint", "trial_design", "dose_regimen", "evidence_phase", "benefit_risk_status"],
        "blocking_uncertainties": ["CHRONIC_NOROVIRUS_DEFINITION_NOT_STANDARDIZED", "MECHANISM_UNCERTAIN", "SMALL_HETEROGENEOUS_EVIDENCE_BASE", "CURRENT_TRIAL_STATUS_REQUIRES_FRESH_VERIFICATION"],
        "candidate_seed": {"intervention": "nitazoxanide", "claim": "EVIDENCE_GAP_NOT_EFFICACY_CLAIM"},
        "evidence_gap": {
            "decision_question": "Does nitazoxanide provide clinically meaningful and virologically durable benefit in chronic norovirus infection in immunocompromised patients?",
            "comparators": ["placebo_or_standard_supportive_care"],
            "required_outcomes": ["symptom_duration", "virologic_clearance", "recurrence_after_withdrawal", "adverse_events"],
            "missing_evidence": ["adequately_powered_current_randomized_evidence", "standardized_chronic_case_definition", "durability_and_recurrence_characterization"],
        },
    },
    217: {
        "problem_type": "BIOLOGIC_DELIVERY_STABILITY",
        "relevant_axes": ["formulation", "dosage_form", "route_of_administration", "gastric_resistance", "release_profile", "storage_stability", "assay_reproducibility", "therapeutic_modality"],
        "blocking_uncertainties": ["IN_VIVO_DELIVERY_EFFECTIVENESS_NOT_ESTABLISHED_BY_FORMULATION_STABILITY_TEST_ALONE", "GENERALIZATION_TO_OTHER_PHAGE_COMPOSITIONS_UNESTABLISHED"],
        "candidate_seed": {"payload": "combined bacteriophage", "search_region": "gastroresistant oral solid dosage-form design"},
    },
    226: {
        "problem_type": "BIOPROCESS_SCALEUP_GAP",
        "relevant_axes": ["bioprocess_growth_rate", "contamination_risk", "assay_cost", "assay_reproducibility"],
        "blocking_uncertainties": ["LARGE_BIOREACTOR_SCALEUP_NOT_ESTABLISHED", "PROCESS_CONTROL_AND_CONTAMINATION_RISK_UNQUANTIFIED"],
        "candidate_seed": {"chassis": "Vibrio natriegens", "product": "succinate", "claim": "BIOPROCESS_RESEARCH_REGION"},
    },
    233: {
        "problem_type": "MODIFIED_RELEASE_FORMULATION_GAP",
        "relevant_axes": ["formulation", "dosage_form", "release_profile", "bioavailability", "exposure_metric", "storage_stability"],
        "blocking_uncertainties": ["TARGET_JOINT_EXPOSURE_PROFILE_REQUIRES_PREDECLARATION", "CLINICAL_BENEFIT_OF_MODIFIED_RELEASE_COMBINATION_NOT_ESTABLISHED_BY_MARKET_GAP"],
        "candidate_seed": {"active_moieties": ["memantine", "citicoline"], "search_region": "joint modified-release exposure profile"},
    },
    237: {
        "problem_type": "SOLUBILITY_LIMITED_DEVELOPABILITY",
        "relevant_axes": ["solubility", "excipient_compatibility", "solubilization_capacity", "formulation", "route_of_administration", "storage_stability", "release_profile"],
        "blocking_uncertainties": ["PARENTERAL_COMPATIBILITY_AND_SAFETY_REQUIRE_VALIDATION", "STABILITY_AND_PRECIPITATION_WINDOW_REQUIRE_MEASUREMENT", "IN_VIVO_PK_NOT_ESTABLISHED"],
        "candidate_seed": {"active_moiety": "3-hydroxyquinazoline derivative (PGH)", "search_region": "parenteral solubilization/formulation rescue"},
    },
    267: {
        "problem_type": "LOW_COST_ANALYTICAL_METHOD_GAP",
        "relevant_axes": ["assay_cost", "assay_reproducibility", "chemistry:analytical_method", "chemistry:instrument_type", "metrology:uncertainty_model", "metrology:repeatability", "metrology:reproducibility"],
        "blocking_uncertainties": ["TRANSFERABILITY_ACROSS_DEVICES_AND_LIGHTING_REQUIRES_VALIDATION", "BIAS_AND_UNCERTAINTY_VS_REFERENCE_METHOD_REQUIRE_PAIRED_ESTIMATION"],
        "candidate_seed": {"assay": "digital colorimetry", "reference": "pharmacopoeial photocolorimetry/spectrophotometry", "claim": "ASSAY_DESIGN_REGION"},
        "quantitative_model_seed": {
            "status": "SOURCE_DERIVED_UNVERIFIED_QUANTITATIVE_MODEL",
            "model_family": "linear RGB concentration calibration",
            "source_printed_page": 269,
            "equations": [
                {"solution": "red", "channel": "R", "slope": -192.14, "intercept": 228.91, "r2": 0.9999},
                {"solution": "red", "channel": "G", "slope": -415.16, "intercept": 105.46, "r2": 0.9996},
                {"solution": "red", "channel": "B", "slope": -126.4, "intercept": 27.523, "r2": 0.9999},
                {"solution": "yellow", "channel": "R", "slope": 165.88, "intercept": 216.44, "r2": 0.9985},
                {"solution": "yellow", "channel": "G", "slope": 145.31, "intercept": 152.83, "r2": 0.9990},
                {"solution": "yellow", "channel": "B", "slope": -559.31, "intercept": 84.793, "r2": 0.9981},
                {"solution": "blue", "channel": "R", "slope": -1068.2, "intercept": 199.77, "r2": 0.9819},
                {"solution": "blue", "channel": "G", "slope": -205.47, "intercept": 196.3, "r2": 0.9941},
                {"solution": "blue", "channel": "B", "slope": 31.272, "intercept": 114.03, "r2": 0.9995}
            ],
            "forward_model": "RGB_channel = slope * concentration + intercept",
            "inverse_model": "concentration = (RGB_channel - intercept) / slope",
            "coefficient_uncertainty_available": False,
            "measurement_noise_model_available": False,
            "world_verified": False
        },
    },
}

# Measurement families are used to build a typed problem graph.  A match records a
# source span and candidate coordinate; it never creates a measured numeric value.
MEASUREMENT_RULES: tuple[dict[str, Any], ...] = (
    {"family": "FORMULATION", "terms": ("ЛЕКАРСТВЕННОЙ ФОРМ", "ЛЕКАРСТВЕННАЯ ФОРМ", "ЛЕКАРСТВЕННЫЕ ФОРМ", "ЛЕКАРСТВЕННЫХ ФОРМ", "ФОРМЫ ВЫПУСКА", "DOSAGE FORM", "ФОРМУЛЯЦ", "МАЗЕВ", "ТАБЛЕТИРОВАН", "КАПСУЛ", "ВСПОМОГАТЕЛЬН", "EXCIPIENT"), "axes": ("formulation", "dosage_form", "excipient_compatibility")},
    {"family": "SOLUBILITY", "terms": ("РАСТВОРИМОСТ", "СОЛЮБИЛ", "SOLUBIL", "МИЦЕЛЛ"), "axes": ("solubility", "solubilization_capacity")},
    {"family": "RELEASE_STABILITY", "terms": ("ВЫСВОБОЖД", "RELEASE", "ГАСТРОРЕЗИСТ", "STABIL", "СТАБИЛЬНОСТ", "РАСПАДАЕМОСТ"), "axes": ("release_profile", "gastric_resistance", "storage_stability")},
    {"family": "POTENCY", "terms": ("IC50", "PIC50", "ИНГИБИ", "POTENCY", "АКТИВНОСТ"), "axes": ("potency_metric",)},
    {"family": "SELECTIVITY_SAFETY", "terms": ("СЕЛЕКТИВ", "SELECTIV", "ТОКСИЧ", "LD50", "БЕЗОПАС"), "axes": ("selectivity_profile", "safety_pharmacology", "off_target_liability")},
    {"family": "PK", "terms": ("ФАРМАКОКИНЕТ", "PHARMACOKINET", "КЛИРЕНС", "ЭЛИМИНАЦ", "TMAX", "БИОДОСТУПНОСТ"), "axes": ("bioavailability", "clearance", "elimination_half_life", "exposure_metric")},
    {"family": "CLINICAL", "terms": ("ПАЦИЕНТ", "РАНДОМИЗ", "PLACEBO", "ПЛАЦЕБО", "КЛИНИЧЕСК", "TRIAL"), "axes": ("target_population", "clinical_endpoint", "trial_design", "evidence_phase")},
    {"family": "ANALYTICAL_METHOD", "terms": ("СПЕКТРОФОТОМ", "ХРОМАТОГРАФ", "ЦВЕТОМЕТР", "ТИТРИМЕТР", "АНАЛИТИЧЕСК", "PHOTOCOLOR", "RGB"), "axes": ("chemistry:analytical_method", "chemistry:instrument_type")},
    {"family": "METROLOGY", "terms": ("ВОСПРОИЗВОД", "ПОВТОРЯЕМОСТ", "ПОГРЕШНОСТ", "НЕОПРЕДЕЛЕННОСТ", "КАЛИБРОВ", "ГРАДУИРОВ"), "axes": ("metrology:uncertainty_model", "metrology:repeatability", "metrology:reproducibility")},
    {"family": "BIOPROCESS", "terms": ("VIBRIO NATRIEGENS", "КУЛЬТИВИР", "БИОРЕАКТОР", "РОСТ БАКТЕР", "КОНТАМИНАЦ", "ФЕРМЕНТАЦ"), "axes": ("bioprocess_growth_rate", "contamination_risk")},
    {"family": "CHEMICAL_SYNTHESIS", "terms": ("СИНТЕЗ", "SYNTHESIS", "ПОЛУЧЕНИЕ", "МЕХАНОХИМИ"), "axes": ("chemistry:reaction_class", "chemistry:intermediate_structure")},
)

DESIGN_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("RANDOMIZED_CONTROLLED", ("РАНДОМИЗИРОВ", "RANDOMIZED", "ПЛАЦЕБО", "PLACEBO")),
    ("QSAR", ("QSAR", "MACHINE LEARNING", "МАШИННОГО ОБУЧЕНИЯ")),
    ("VIRTUAL_SCREENING", ("ВИРТУАЛЬНЫЙ СКРИНИНГ", "VIRTUAL SCREENING")),
    ("IN_VITRO", ("IN VITRO", "IN VITRO")),
    ("IN_VIVO", ("IN VIVO", "ЖИВОТН", "КРЫС", "ДРОЗОФИЛ")),
    ("ANALYTICAL_COMPARISON", ("В СРАВНЕНИИ", "СРАВН", "REFERENCE METHOD", "СТАНДАРТНОЙ МЕТОДИК")),
    ("FORMULATION_DEVELOPMENT", ("РАЗРАБОТК", "ЛЕКАРСТВЕННОЙ ФОРМ", "ФАРМАЦЕВТИЧЕСКОЙ РАЗРАБОТ")),
    ("LITERATURE_REVIEW", ("АНАЛИЗ СУЩЕСТВУЮЩИХ ЛИТЕРАТУРНЫХ ДАННЫХ", "ОБЗОР", "REVIEW")),
)

LIMITATION_TERMS = (
    "ОГРАНИЧ", "НЕОБХОДИМ", "ТРЕБУЕТ", "НЕ УСТАНОВ", "НЕ ИЗУЧ", "НЕИЗВЕСТ", "ОТСУТСТВ", "МАЛО ИССЛЕДОВ", "ДАЛЬНЕЙШ",
    "LIMIT", "REQUIR", "UNKNOWN", "NOT ESTABLISHED", "FURTHER STUD",
)
COMPARATOR_TERMS = ("ПЛАЦЕБО", "PLACEBO", "СРАВН", "В СРАВНЕНИИ", "КОНТРОЛ", "СТАНДАРТН", "REFERENCE")
INTERVENTION_TERMS = ("ПРИМЕНЯЛ", "ИСПОЛЬЗОВАЛ", "ЛЕЧЕНИ", "ВВЕДЕН", "ВВОДИЛ", "СОЛЮБИЛИЗАТОР", "ЭМУЛЬС", "ЭКСТРАКТ", "ПРЕПАРАТ", "СОЕДИНЕНИ")
SYSTEM_TERMS = ("ПАЦИЕНТ", "КРЫС", "ДРОЗОФИЛ", "БАКТЕР", "КЛЕТК", "РАСТВОР", "СЫРЬ", "ТАБЛЕТ", "МАЗ", "СОЕДИНЕНИ", "МОДЕЛ")


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def trim_to_article_start(text: str, title: str) -> str:
    """Remove previous-article tail from a shared printed start page.

    TOC page numbers identify the page on which an article starts, not necessarily
    the first line of that page.  Semantic extraction therefore begins at the
    article's own heading, preventing cross-article keyword leakage.
    """
    normalized = clean(text)
    t = clean(title)
    pos = normalized.upper().find(t.upper())
    if pos >= 0:
        return normalized[pos:]
    words = [w for w in re.findall(r"[A-ZА-ЯЁ0-9]+", t.upper()) if len(w) >= 4]
    for n in (6, 5, 4, 3):
        if len(words) >= n:
            phrase = " ".join(words[:n])
            p = normalized.upper().find(phrase)
            if p >= 0:
                return normalized[p:]
    return normalized




def extract_between(text: str, starts: tuple[str, ...], ends: tuple[str, ...], max_chars: int = 2200) -> str:
    pos = -1
    marker = ""
    for s in starts:
        p = text.find(s)
        if p >= 0 and (pos < 0 or p < pos):
            pos, marker = p, s
    if pos < 0:
        return ""
    body = text[pos + len(marker):]
    epos = len(body)
    for e in ends:
        p = body.find(e)
        if p >= 0:
            epos = min(epos, p)
    return clean(body[:epos])[:max_chars]


def sentences(text: str) -> list[str]:
    text = clean(text)
    if not text:
        return []
    rows = re.split(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁ0-9])", text)
    return [clean(x) for x in rows if len(clean(x)) >= 12]


def evidence_spans(text: str, terms: Iterable[str], max_spans: int = 3, max_chars: int = 420) -> list[str]:
    up_terms = tuple(str(x).upper() for x in terms)
    out: list[str] = []
    for row in sentences(text):
        u = row.upper()
        if any(term in u for term in up_terms):
            out.append(row[:max_chars])
            if len(out) >= max_spans:
                break
    return out


def parse_toc(reader: PdfReader) -> list[dict[str, Any]]:
    text = "\n".join(reader.pages[i].extract_text() or "" for i in range(4, 13))
    lines = [clean(x) for x in text.splitlines() if clean(x)]
    entries: list[tuple[int, list[str]]] = []
    buf: list[str] = []
    for line in lines:
        if re.fullmatch(r"\d{2,3}", line) and 14 <= int(line) <= 271:
            entries.append((int(line), list(buf)))
            buf.clear()
        else:
            buf.append(line)
    if len(entries) != 60:
        raise AssertionError(f"expected 60 TOC articles, got {len(entries)}")
    out = []
    for i, (printed, block) in enumerate(entries):
        author_idx = -1
        for j, line in enumerate(block):
            if "." in line and re.search(r"[А-ЯA-ZЁ]\s*\.", line):
                author_idx = j
        title = TITLE_OVERRIDES.get(printed) or clean(" ".join(block[author_idx + 1:]))
        pdf_start = printed + 1
        pdf_end = entries[i + 1][0] if i + 1 < len(entries) else 274
        out.append({"printed_start_page": printed, "pdf_start_page": pdf_start, "pdf_end_page": pdf_end, "title": title})
    return out


def _field(text: str, terms: Iterable[str]) -> dict[str, Any]:
    spans = evidence_spans(text, terms)
    return {"status": "SOURCE_SPANS_PRESENT" if spans else "NOT_EXTRACTED_FROM_SOURCE", "source_spans": spans}


def build_typed_problem_graph(title: str, abstract: str, goal: str, methods: str, results: str, conclusion: str, full_text: str) -> dict[str, Any]:
    scientific_text = clean(" ".join(x for x in (title, abstract, goal, methods, results, conclusion) if x))
    measurements = []
    evidence_axes: set[str] = {"evidence_provenance"}
    for rule in MEASUREMENT_RULES:
        spans = evidence_spans(scientific_text, rule["terms"])
        if spans:
            measurements.append({"family": rule["family"], "axes": list(rule["axes"]), "source_spans": spans})
            evidence_axes.update(rule["axes"])
    design = []
    upper = scientific_text.upper()
    for label, terms in DESIGN_RULES:
        if any(term in upper for term in terms):
            design.append(label)
    limitations = evidence_spans(clean((results + " " + conclusion + " " + full_text[-6000:])), LIMITATION_TERMS, max_spans=5)
    graph = {
        "schema": "phi-pharmaceutical-typed-problem-graph/v8.3",
        "extraction_policy": "SOURCE_SPAN_ONLY_NO_WORLD_TRUTH_NO_HIDDEN_INFERENCE",
        "goal": {"status": "SOURCE_EXPLICIT" if goal else ("ABSTRACT_FALLBACK" if abstract else "TITLE_FALLBACK"), "text": (goal or abstract or title)[:1800]},
        "system": _field(scientific_text, SYSTEM_TERMS),
        "intervention": _field(scientific_text, INTERVENTION_TERMS),
        "comparator": _field(scientific_text, COMPARATOR_TERMS),
        "measurements": measurements,
        "results": {"status": "SOURCE_EXPLICIT" if results else ("CONCLUSION_FALLBACK" if conclusion else "NOT_EXTRACTED_FROM_SOURCE"), "text": (results or conclusion)[:2400]},
        "limits": {"status": "SOURCE_SPANS_PRESENT" if limitations else "NO_EXPLICIT_LIMITATION_SPAN_EXTRACTED", "source_spans": limitations},
        "study_design_signals": design,
        "evidence_supported_axes": sorted(evidence_axes),
        "numeric_values_invented": False,
        "causal_claim_invented": False,
        "operator_assigned_by_single_keyword": False,
    }
    return graph


def operator_eligibility(graph: dict[str, Any], title: str, abstract: str, goal: str, methods: str, results: str, conclusion: str) -> dict[str, Any]:
    text = clean(" ".join((title, abstract, goal, methods, results, conclusion)))
    upper = text.upper()
    families = {m["family"] for m in graph.get("measurements", ())}
    design = set(graph.get("study_design_signals", ()))

    def record(eligible: bool, reason: str, terms: Iterable[str] = ()) -> dict[str, Any]:
        spans = evidence_spans(text, terms, max_spans=4) if terms else []
        return {"status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE", "reason": reason, "source_spans": spans}

    explicit_formulation = any(k in upper for k in ("ЛЕКАРСТВЕННОЙ ФОРМ", "ЛЕКАРСТВЕННАЯ ФОРМ", "ЛЕКАРСТВЕННЫЕ ФОРМ", "ЛЕКАРСТВЕННЫХ ФОРМ", "ФОРМЫ ВЫПУСКА", "DOSAGE FORM", "СОЛЮБИЛИЗ", "МАЗЕВ", "МОДИФИЦИРОВАНН", "ВСПОМОГАТЕЛЬН"))
    formulation_manipulation = (
        "FORMULATION_DEVELOPMENT" in design
        or any(k in upper for k in ("СОЛЮБИЛИЗ", "МОДИФИЦИРОВАНН", "ВСПОМОГАТЕЛЬН", "РАСПАДАЕМОСТ", "ПОДБОР ОПТИМАЛЬН"))
        or ("СОСТАВ" in upper and any(k in upper for k in ("МАЗЕВ", "ТАБЛЕТ", "КАПСУЛ", "ЛЕКАРСТВЕНН")))
    )
    formulation = explicit_formulation and formulation_manipulation and "FORMULATION" in families and bool(families & {"SOLUBILITY", "RELEASE_STABILITY", "PK"})

    biologic_payload = any(k in upper for k in ("БАКТЕРИОФАГ", "PHAGE", "ФАГОПРЕПАРАТ"))
    delivery_challenge = any(k in upper for k in ("ГАСТРОРЕЗИСТ", "ОТСРОЧЕНН", "КИШЕЧН", "DELIVERY", "ВЫСВОБОЖД"))
    delivery = biologic_payload and delivery_challenge and "RELEASE_STABILITY" in families

    target_or_inhibitor = any(k in upper for k in ("HDAC6", "COX-2", "ЦИКЛООКСИГЕНАЗ", "ИНГИБИТОР"))
    model_screen = bool(design & {"QSAR", "VIRTUAL_SCREENING"})
    quantitative_activity = any(k in upper for k in ("IC50", "PIC50", "PCHemBL".upper(), "ИНГИБИРОВ"))
    medchem = target_or_inhibitor and model_screen and ("POTENCY" in families or quantitative_activity)

    cost_motive = any(k in upper for k in ("ВЫСОКОЙ СТОИМОСТ", "ВЫСОКАЯ СТОИМОСТ", "ЭКОНОМИЧНЫХ МЕТОД", "ЭКОНОМИЧНЫЙ МЕТОД", "ДОСТУПНЫЙ МЕТОД", "ДОСТУПЕН БОЛЬШИНСТВ", "НЕ ТРЕБУЕТ СПЕЦИАЛЬНОГО ОБОРУДОВАН", "НИЗКОЙ СТОИМОСТ", "LOW COST"))
    reference_compare = any(k in upper for k in ("В СРАВНЕНИИ", "СРАВН", "СТАНДАРТНОЙ МЕТОДИК", "ФАРМАКОПЕ", "REFERENCE"))
    low_cost = "ANALYTICAL_METHOD" in families and cost_motive and reference_compare

    rows = {
        "FORMULATION_RESCUE": record(formulation, "explicit dosage-form/developability problem plus formulation and property measurements required", ("ЛЕКАРСТВЕННОЙ ФОРМ", "СОЛЮБИЛ", "РАСПАДАЕМОСТ", "ВЫСВОБОЖД")),
        "DELIVERY_RESCUE": record(delivery, "biologic payload plus explicit delivery/release challenge required", ("БАКТЕРИОФАГ", "ГАСТРОРЕЗИСТ", "ВЫСВОБОЖД")),
        "MULTIOBJECTIVE_MEDCHEM_SEARCH": record(medchem, "target/inhibitor context plus QSAR/virtual-screen design and potency signal required", ("QSAR", "ВИРТУАЛЬНЫЙ СКРИНИНГ", "HDAC6", "ЦИКЛООКСИГЕНАЗ", "IC50")),
        "LOW_COST_ASSAY_DESIGN": record(low_cost, "analytical method plus explicit cost/accessibility motive and reference comparison required", ("СТОИМОСТ", "ДОСТУП", "ЦВЕТОМЕТР", "СРАВН", "ФАРМАКОПЕ")),
    }
    eligible = [op for op, row in rows.items() if row["status"] == "ELIGIBLE"]
    if set(eligible) == {"FORMULATION_RESCUE", "DELIVERY_RESCUE"} and delivery:
        selected = "DELIVERY_RESCUE"
        status = "OPERATOR_SELECTED_SPECIFIC_DELIVERY_OVER_FORMULATION_PARENT"
    elif len(eligible) == 1:
        selected = eligible[0]
        status = "OPERATOR_SELECTED_FROM_TYPED_SEMANTIC_EVIDENCE"
    elif not eligible:
        selected = "NONE_SOURCE_CONTEXT_ONLY"
        status = "ABSTAIN_NO_OPERATOR_ELIGIBILITY"
    else:
        selected = "NONE_SOURCE_CONTEXT_ONLY"
        status = "ABSTAIN_AMBIGUOUS_OPERATOR_ELIGIBILITY"
    return {
        "schema": "phi-pharmaceutical-operator-eligibility/v8.3",
        "status": status,
        "selected_operator": selected,
        "eligible_operators": eligible,
        "operators": rows,
        "abstention_is_valid_output": True,
        "scientific_status_modified": False,
    }


def semantic_problem_type(graph: dict[str, Any], adjudication: dict[str, Any]) -> str:
    op = adjudication["selected_operator"]
    if op == "FORMULATION_RESCUE":
        return "FORMULATION_OR_DEVELOPABILITY"
    if op == "DELIVERY_RESCUE":
        return "DELIVERY_OR_RELEASE"
    if op == "MULTIOBJECTIVE_MEDCHEM_SEARCH":
        return "MULTIOBJECTIVE_MEDCHEM_GAP"
    if op == "LOW_COST_ASSAY_DESIGN":
        return "LOW_COST_ANALYTICAL_METHOD_GAP"
    design = set(graph.get("study_design_signals", ()))
    families = {m["family"] for m in graph.get("measurements", ())}
    if "CLINICAL" in families or "RANDOMIZED_CONTROLLED" in design:
        return "CLINICAL_OR_EVIDENCE_RESEARCH_PROBLEM"
    if "BIOPROCESS" in families:
        return "BIOPROCESS_RESEARCH"
    if "ANALYTICAL_METHOD" in families:
        return "ANALYTICAL_OR_STANDARDIZATION_RESEARCH_PROBLEM"
    if "CHEMICAL_SYNTHESIS" in families:
        return "CHEMISTRY_RESEARCH_PROBLEM"
    return "SOURCE_DERIVED_RESEARCH_PROBLEM"


def build(pdf_path: Path, root: Path = ROOT) -> dict[str, Any]:
    raw = pdf_path.read_bytes()
    actual_sha = sha256_bytes(raw)
    if actual_sha != SOURCE_SHA256:
        raise AssertionError(f"source PDF sha mismatch: {actual_sha}")
    reader = PdfReader(str(pdf_path))
    if len(reader.pages) != 274:
        raise AssertionError(f"expected 274 pages, got {len(reader.pages)}")
    toc = parse_toc(reader)
    operator_specs = PharmaceuticalResearchOperatorOwner().contract()["operators"]

    articles = []
    problems = []
    for idx, meta in enumerate(toc, 1):
        page_texts = [(reader.pages[p - 1].extract_text() or "") for p in range(meta["pdf_start_page"], meta["pdf_end_page"] + 1)]
        page_text = "\n".join(page_texts)
        title = meta["title"]
        text = trim_to_article_start(page_text, title)
        abstract = extract_between(text, ("Аннотация:", "Аннотация."), ("Abstract:", "Ключевые слова:"), 1800)
        goal = extract_between(text, ("Цель исследования.", "Цель исследования:", "Цель работы -", "Цель работы.", "Целью работы", "Целью исследования"), ("Материалы и методы", "Материалы", "Результаты исследования"), 1800)
        methods = extract_between(text, ("Материалы и методы исследования.", "Материалы и методы исследования:", "Материалы и методы.", "Материалы и методы:"), ("Результаты исследования", "Результаты и их обсуждение", "Результаты"), 2600)
        results = extract_between(text, ("Результаты исследования и их обсуждение.", "Результаты исследования и их обсуждения.", "Результаты и их обсуждение.", "Результаты."), ("Выводы.", "Выводы:", "Вывод.", "Вывод:", "Список литературы"), 3000)
        conclusion = extract_between(text, ("Выводы.", "Выводы:", "Вывод.", "Вывод:"), ("Список литературы",), 2400)
        article_id = f"KEMGMU-2024-A{idx:02d}-P{meta['printed_start_page']:03d}"
        page_digest = sha256_bytes(clean(page_text).encode("utf-8"))
        article_text_digest = sha256_bytes(clean(text).encode("utf-8"))
        graph = build_typed_problem_graph(title, abstract, goal, methods, results, conclusion, text)
        adjudication = operator_eligibility(graph, title, abstract, goal, methods, results, conclusion)
        operator = adjudication["selected_operator"]
        context = DEEP_CONTEXT.get(meta["printed_start_page"], {})
        ptype = str(context.get("problem_type", semantic_problem_type(graph, adjudication)))

        evidence_axes = set(graph.get("evidence_supported_axes", ()))
        evidence_axes.update(context.get("relevant_axes", ()))
        operator_required_axes: list[str] = []
        if operator != "NONE_SOURCE_CONTEXT_ONLY":
            spec = operator_specs[operator]
            operator_required_axes.extend(spec.get("required_pharmaceutical_axes", ()))
            operator_required_axes.extend(spec.get("cross_domain_axes", ()))
        relevant_axes = sorted(evidence_axes | set(operator_required_axes))

        article = {
            "article_id": article_id,
            "title": title,
            "printed_start_page": meta["printed_start_page"],
            "pdf_start_page": meta["pdf_start_page"],
            "pdf_end_page": meta["pdf_end_page"],
            "page_text_sha256": page_digest,
            "article_text_sha256": article_text_digest,
            "semantic_start_trimmed_to_article_heading": clean(page_text) != clean(text),
            "abstract_excerpt": abstract,
            "goal_excerpt": goal,
            "methods_excerpt": methods,
            "results_excerpt": results,
            "conclusion_excerpt": conclusion,
            "source_status": "SOURCE_DERIVED_UNVERIFIED",
            "typed_problem_graph_digest": sha256_bytes(json.dumps(graph, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")),
        }
        articles.append(article)

        claims = []
        if abstract:
            claims.append({"claim_id": f"{article_id}-ABSTRACT", "relation": "SOURCE_STATES", "text": abstract[:900], "active_evidence": False})
        if conclusion:
            claims.append({"claim_id": f"{article_id}-CONCLUSION", "relation": "SOURCE_STATES", "text": conclusion[:1200], "active_evidence": False})
        record = {
            "problem_id": f"PHARMA-PROBLEM-{idx:02d}",
            "article_id": article_id,
            "title": title,
            "problem_type": ptype,
            "problem_statement": (goal or abstract or title)[:1800],
            "source_locator": {
                "source_document_name": SOURCE_NAME,
                "source_document_sha256": SOURCE_SHA256,
                "pdf_start_page": meta["pdf_start_page"],
                "pdf_end_page": meta["pdf_end_page"],
                "pdf_total_pages": 274,
                "printed_start_page": meta["printed_start_page"],
            },
            "source_derived_claims": claims,
            "typed_problem_graph": graph,
            "operator_adjudication": adjudication,
            "evidence_supported_axes": sorted(evidence_axes),
            "operator_required_axes": sorted(set(operator_required_axes)),
            "relevant_axes": relevant_axes,
            "research_operator": operator,
            "candidate_seed": context.get("candidate_seed", {"status": "NOT_MATERIALIZED_FROM_SOURCE_CONTEXT_ONLY"}),
            "blocking_uncertainties": context.get("blocking_uncertainties", ["WORLD_SOURCE_VERIFICATION_REQUIRED", "PROBLEM_SPECIFIC_CAUSAL_OR_EXPERIMENTAL_GAPS_NOT_YET_ADJUDICATED"]),
            "semantic_adjudication_source": "DEEP_CURATED_PLUS_TYPED_GRAPH" if context else "TYPED_GRAPH",
            "quantitative_model_seed": context.get("quantitative_model_seed", {}),
        }
        if "evidence_gap" in context:
            record["evidence_gap"] = context["evidence_gap"]
        problems.append(record)

    source_catalog = {
        "schema": "phi-pharmaceutical-source-collection-catalog/v8.3",
        "source_document": {"name": SOURCE_NAME, "sha256": SOURCE_SHA256, "pdf_total_pages": 274, "toc_pdf_pages": [5, 13], "article_content_pdf_pages": [15, 274]},
        "article_count": len(articles),
        "articles": articles,
        "claim_boundary": "Parsed source excerpts and typed problem graphs are audit material, not WORLD-verified evidence.",
    }
    operator_counts = {op: sum(p["research_operator"] == op for p in problems) for op in operator_specs}
    abstain_count = sum(p["research_operator"] == "NONE_SOURCE_CONTEXT_ONLY" for p in problems)
    atlas = {
        "schema": "phi-pharmaceutical-problem-atlas-source/v8.3",
        "source_collection": source_catalog["source_document"],
        "problem_count": len(problems),
        "deep_curated_problem_count": len(DEEP_CONTEXT),
        "typed_problem_graph_count": len(problems),
        "operator_adjudication_count": len(problems),
        "operator_counts": operator_counts,
        "abstain_count": abstain_count,
        "problems": problems,
        "claim_boundary": {
            "source_document_is_world_verified_by_local_presence": False,
            "source_derived_claim_is_active_evidence": False,
            "typed_problem_graph_is_world_truth": False,
            "operator_eligibility_is_scientific_promotion": False,
            "new_drug_discovered": False,
            "clinical_recommendation": False,
        },
    }
    out_dir = root / "data" / "pharmaceutical"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "conference_2024_source_catalog_v8_3.json").write_text(json.dumps(source_catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "pharmaceutical_problem_atlas_v8_3.json").write_text(json.dumps(atlas, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    coverage = set()
    for a in articles:
        coverage.update(range(int(a["pdf_start_page"]), int(a["pdf_end_page"]) + 1))
    build_receipt = {
        "schema": "phi-pharmaceutical-problem-atlas-source-build/v8.3",
        "source_document_name": SOURCE_NAME,
        "source_document_sha256": actual_sha,
        "source_pdf_page_count": len(reader.pages),
        "toc_article_count": len(articles),
        "problem_count": len(problems),
        "deep_curated_problem_count": len(DEEP_CONTEXT),
        "typed_problem_graph_count": len(problems),
        "operator_adjudication_count": len(problems),
        "abstain_count": abstain_count,
        "operator_counts": operator_counts,
        "article_content_coverage_pdf_pages": [min(coverage), max(coverage)] if coverage else [],
        "article_content_page_count": len(coverage),
        "article_content_contiguous_15_to_274": coverage == set(range(15, 275)),
        "blanket_keyword_operator_lowering_removed": True,
        "abstention_supported": True,
        "source_local_presence_is_world_verification": False,
        "source_claims_require_scientific_verification_core": True,
    }
    build_receipt["digest"] = hashlib.sha256(json.dumps(build_receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pharmaceutical_problem_atlas_source_build_v8_3.json").write_text(json.dumps(build_receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"source_catalog": source_catalog, "atlas": atlas, "build_receipt": build_receipt}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: python -m evaluation.build_pharmaceutical_problem_atlas_v8_3 <source.pdf> [root]")
    pdf = Path(sys.argv[1])
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT
    result = build(pdf, root)
    print(json.dumps({
        "article_count": result["source_catalog"]["article_count"],
        "problem_count": result["atlas"]["problem_count"],
        "typed_problem_graph_count": result["atlas"]["typed_problem_graph_count"],
        "operator_counts": result["atlas"]["operator_counts"],
        "abstain_count": result["atlas"]["abstain_count"],
        "source_sha256": result["source_catalog"]["source_document"]["sha256"],
    }, ensure_ascii=False, indent=2))
