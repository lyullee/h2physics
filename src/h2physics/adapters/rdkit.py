"""Optional native molecule identity; no molecular parser is reimplemented."""

from collections import Counter
from dataclasses import dataclass

from ..reactions import ChemicalSpecies


@dataclass(frozen=True, slots=True)
class MolecularIdentity:
    species: ChemicalSpecies
    canonical_smiles: str
    native_molecule: object
    provider_version: str


def molecule_from_smiles(smiles: str, *, identifier: str, phase: str) -> MolecularIdentity:
    from rdkit import Chem, rdBase
    from rdkit.Chem import Descriptors

    if not isinstance(smiles, str) or not smiles.strip():
        raise ValueError("A nonempty molecular SMILES string is required")
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None or molecule.GetNumAtoms() == 0:
        raise ValueError("Native RDKit rejected the molecular structure")
    if any(a.GetIsotope() for a in molecule.GetAtoms()):
        raise ValueError("This composition contract requires an explicit future isotope basis")
    if any(a.GetNumRadicalElectrons() for a in molecule.GetAtoms()):
        raise ValueError("This molecular screening level requires closed-shell structures")
    explicit = Chem.AddHs(molecule)
    elements = dict(Counter(a.GetSymbol() for a in explicit.GetAtoms()))
    species = ChemicalSpecies(identifier, elements, Descriptors.MolWt(molecule)/1000,
                              phase, sum(a.GetFormalCharge() for a in molecule.GetAtoms()))
    return MolecularIdentity(species, Chem.MolToSmiles(molecule, canonical=True),
                             molecule, rdBase.rdkitVersion)
