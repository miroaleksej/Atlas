from .ai_lab import (
    AIBudgetVector,
    JsonCommandBackend,
    LaboratoryCapabilityOwner,
    ModelBackendSpec,
    ModelExecutionBackend,
    ModelExecutionOwner,
    ModelRunRequest,
    ModelRunResult,
    ModelScale,
    BUDGET_CAPABILITIES,
    REGIME_CAPABILITIES,
    REQUIRED_FRONTIER_CAPABILITIES,
)
"""ScienceAtlas AI v0.10.0."""
from .frontier003 import DEFAULT_REGIMES, execute_frontier003, load_manifest, materialize_results_template
from .methodology import (
    ConventionInvariantOwner,
    DataCollapseOwner,
    DimensionalMethodOwner,
    KnownLawDerivabilityOwner,
    PipelineNullCalibrationOwner,
    PiTransitionOwner,
    RegimeHoldoutOwner,
    SystemCoverageOwner,
)
from .owners import (
    AdaptiveSubspaceExplorerOwner,
    MultiAxisMechanismOwner,
    NumericMechanismOwner,
    HypergraphRouteOwner,
    OwnerBus,
    OwnerSpec,
    RepresentationProposalOwner,
    ResidualFrontierOwner,
)
from .persistence import load_state, save_state
from .runtime import ScienceAtlasAI
from .types import (
    Axis,
    AxisSymbolBinding,
    CriticVector,
    DimensionHypothesisProfile,
    HypergraphRoute,
    EvidenceRecord,
    ExperimentPlan,
    FrontierAssessment,
    FrontierAxisScore,
    Hypothesis,
    KnownMonomialRelation,
    Observation,
    RepresentationProposal,
    ScalarResidue,
    SubspaceCandidate,
    SubspaceSearchState,
    SemanticQuantity,
    ValidationOutcome,
    ValidityDomain,
)

__version__ = ScienceAtlasAI.VERSION

__all__ = [
    "DEFAULT_REGIMES",
    "execute_frontier003",
    "load_manifest",
    "materialize_results_template",
    "AIBudgetVector",
    "BUDGET_CAPABILITIES",
    "JsonCommandBackend",
    "LaboratoryCapabilityOwner",
    "ModelBackendSpec",
    "ModelExecutionBackend",
    "ModelExecutionOwner",
    "ModelRunRequest",
    "ModelRunResult",
    "ModelScale",
    "REGIME_CAPABILITIES",
    "REQUIRED_FRONTIER_CAPABILITIES",
    "AdaptiveSubspaceExplorerOwner",
    "Axis",
    "AxisSymbolBinding",
    "ConventionInvariantOwner",
    "CriticVector",
    "DataCollapseOwner",
    "DimensionHypothesisProfile",
    "DimensionalMethodOwner",
    "HypergraphRoute",
    "EvidenceRecord",
    "ExperimentPlan",
    "FrontierAssessment",
    "FrontierAxisScore",
    "Hypothesis",
    "HypergraphRouteOwner",
    "KnownLawDerivabilityOwner",
    "KnownMonomialRelation",
    "MultiAxisMechanismOwner",
    "NumericMechanismOwner",
    "Observation",
    "OwnerBus",
    "OwnerSpec",
    "PipelineNullCalibrationOwner",
    "PiTransitionOwner",
    "RegimeHoldoutOwner",
    "SystemCoverageOwner",
    "RepresentationProposal",
    "RepresentationProposalOwner",
    "ResidualFrontierOwner",
    "ScalarResidue",
    "SubspaceCandidate",
    "SubspaceSearchState",
    "ScienceAtlasAI",
    "SemanticQuantity",
    "ValidationOutcome",
    "ValidityDomain",
    "load_state",
    "save_state",
]

from .continual import AlphaLedger, GenesisState, RegionalMetaLearner
from .operator_genesis import (
    FamilySpec, GenesisBudget, GenesisSplit, OperatorCertificate,
    OperatorGenesisOwner, OperatorGrammar, SynthesizedMechanismOwner, TermSpec,
)
from .research_loop import AcquisitionRequest, LoopBudget, LoopState, ResearchLoopOwner, source_spec
from .system import ResearchSystem
__all__ += [
    "AlphaLedger", "GenesisState", "RegionalMetaLearner",
    "FamilySpec", "GenesisBudget", "GenesisSplit", "OperatorCertificate",
    "OperatorGenesisOwner", "OperatorGrammar", "SynthesizedMechanismOwner", "TermSpec",
    "AcquisitionRequest", "LoopBudget", "LoopState", "ResearchLoopOwner", "source_spec",
    "ResearchSystem",
]

from .epoch_genesis import (
    EpochGenesisDirector, EpochPlan, EpochRecord, LedgerBinding,
    SequentialPermutationNullOwner, TriggerBudget as EpochTriggerBudget,
    TriggerState as EpochTriggerState, permutations_required,
)
__all__ += [
    "EpochGenesisDirector", "EpochPlan", "EpochRecord", "LedgerBinding",
    "SequentialPermutationNullOwner", "EpochTriggerBudget",
    "EpochTriggerState", "permutations_required",
]

from .permutation_eprocess import (
    EProcessEpochPlan, EProcessEpochRecord, GainPowerMixture,
    PermutationEProcessOwner, PermutationEProcessState, PermutationGroup,
)
__all__ += [
    "EProcessEpochPlan", "EProcessEpochRecord", "GainPowerMixture",
    "PermutationEProcessOwner", "PermutationEProcessState", "PermutationGroup",
]
