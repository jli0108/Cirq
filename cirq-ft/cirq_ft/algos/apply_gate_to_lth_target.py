# Copyright 2023 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools
from typing import Callable, Sequence

import attr
import cirq
from cirq._compat import cached_property
from cirq_ft import infra
from cirq_ft.algos import unary_iteration_gate


@attr.frozen
class ApplyGateToLthQubit(unary_iteration_gate.UnaryIterationGate):
    r"""A controlled SELECT operation for single-qubit gates.

    $$
    \mathrm{SELECT} = \sum_{l}|l \rangle \langle l| \otimes [G(l)]_l
    $$

    Where $G$ is a function that maps an index to a single-qubit gate.

    This gate uses the unary iteration scheme to apply `nth_gate(selection)` to the
    `selection`-th qubit of `target` all controlled by the `control` register.

    Args:
        selection_regs: Indexing `select` registers of type `SelectionRegisters`. It also contains
            information about the iteration length of each selection register.
        nth_gate: A function mapping the composite selection index to a single-qubit gate.
        control_regs: Control registers for constructing a controlled version of the gate.

    References:
            [Encoding Electronic Spectra in Quantum Circuits with Linear T Complexity]
        (https://arxiv.org/abs/1805.03662).
        Babbush et. al. (2018). Section III.A. and Figure 7.
    """
    selection_regs: infra.SelectionRegisters
    nth_gate: Callable[..., cirq.Gate]
    control_regs: infra.Registers = infra.Registers.build(control=1)

    @classmethod
    def make_on(
        cls, *, nth_gate: Callable[..., cirq.Gate], **quregs: Sequence[cirq.Qid]
    ) -> cirq.Operation:
        """Helper constructor to automatically deduce bitsize attributes."""
        return cls(
            infra.SelectionRegisters.build(
                selection=(len(quregs['selection']), len(quregs['target']))
            ),
            nth_gate=nth_gate,
            control_regs=infra.Registers.build(control=len(quregs['control'])),
        ).on_registers(**quregs)

    @cached_property
    def control_registers(self) -> infra.Registers:
        return self.control_regs

    @cached_property
    def selection_registers(self) -> infra.SelectionRegisters:
        return self.selection_regs

    @cached_property
    def target_registers(self) -> infra.Registers:
        return infra.Registers.build(target=self.selection_registers.total_iteration_size)

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        wire_symbols = ["@"] * self.control_registers.bitsize
        wire_symbols += ["In"] * self.selection_registers.bitsize
        for it in itertools.product(*[range(x) for x in self.selection_regs.iteration_lengths]):
            wire_symbols += [str(self.nth_gate(*it))]
        return cirq.CircuitDiagramInfo(wire_symbols=wire_symbols)

    def nth_operation(  # type: ignore[override]
        self,
        context: cirq.DecompositionContext,
        control: cirq.Qid,
        target: Sequence[cirq.Qid],
        **selection_indices: int,
    ) -> cirq.OP_TREE:
        selection_idx = tuple(selection_indices[reg.name] for reg in self.selection_regs)
        target_idx = self.selection_registers.to_flat_idx(*selection_idx)
        return self.nth_gate(*selection_idx).on(target[target_idx]).controlled_by(control)
