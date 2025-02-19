# Copyright (c) 2023-2024 Salah Berra and contributors
# Distributed under the the GNU General Public License (See accompanying file
# LICENSE or copy at https://www.gnu.org/licenses/)

"""Deep unfolding versions of the conventional iterative methods."""

import logging

import torch
import torch.nn as nn
from torch import Tensor

from .utils import _decompose_matrix, _device

# Create a logger for this module
_logger = logging.getLogger(__name__)
"""Logger for this module."""


class UnfoldingNet(nn.Module):

    A: Tensor
    """Matrix $A$ of the linear system."""

    D: Tensor
    """Diagonal matrix $D$."""

    L: Tensor
    """Lower triangular matrix $L$."""

    U: Tensor
    """Upper triangular matrix $U$."""

    H: Tensor
    """Matrix $H$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution of the linear equation."""

    def __init__(
        self,
        h: Tensor,
        bs: int,
        y: Tensor,
        device: torch.device = _device,
    ):

        self._H = h
        self._bs = bs
        self._y = y
        self._device = device
        self._solved = False
        
        self._s_hats = []
        
        super().__init__()
        self.device = device
        
        self._A, self._D, self._L, self._U, self._Dinv, self._Minv = _decompose_matrix(
            h, device
        )
        
        _logger.info(f"Code run on : {_device}")
    
    def s_hat(self) -> Tensor:
        """Final solution, obtained after all the solver iterations."""
        if not self._solved:
            raise RuntimeError("Problem has not been solved yet!")
        return self._s_hats[-1]
    
    def _evaluate(
        self,
        iter: int,
        solution: Tensor,
        device: torch.device = _device,
    ) -> float:
        """Low-level evaluation of the method's solution.

        Args:
          iter: Evaluate the solution at this iteration.
          solution: The actual solution to the problem.

        Returns:
          The MSE between the real solution and the solution found by the method
            after `iter` iterations.
        """
        return (
            torch.norm(solution.to(device) - self._s_hats[iter].to(device)) ** 2
        ).item() / (self._A.shape[0] * self._bs)

    def evaluate_final(
        self,
        solution: Tensor,
    ) -> float:
        """Evaluate the final solution found by the method.

        Args:
          solution: The actual solution to the problem.

        Returns:
          The MSE between the real solution and the final solution found by the
            method.
        """
        if not self._solved:
            raise RuntimeError("Problem has not been solved yet!")

        return self._evaluate(-1, solution, self._device)

    def evaluate_all(
        self,
        solution: Tensor,
    ) -> list[float]:
        """Evaluate solutions found by the method during all iterations.

        Args:
          solution: The actual solution to the problem.

        Returns:
          A list containing the MSE between the real solution and the solutions
            found by the method during the iterative process.
        """
        if not self._solved:
            raise RuntimeError("Problem has not been solved yet!")

        return [
            self._evaluate(i, solution, self._device) for i in range(len(self._s_hats))
        ]
    
    def forward(self, num_itr: int = 25) : 
        pass

    def deep_train(
        self,
        optimizer: torch.optim.Optimizer,
        loss_func: torch.nn.Module,
        A: Tensor,
        b: Tensor,
        total_itr: int = 25,
        num_batch: int = 10000,
    ) -> list[float]:
        """Train the given model using the specified optimizer and loss function.

        Args:
          optimizer: The optimizer to use for training.
          loss_func: The loss function to use for training.
          total_itr: The total number of iterations (generations) for training.
          A: The initial matrix.
          b: The solution of the linear problem
          num_batch: The number of batches per iteration.

        Returns:
          The list of loss values per iteration.
        """
        loss_gen = []
        for gen in range(total_itr):
            for i in range(num_batch):
                optimizer.zero_grad()
                x_hat, _ = self(gen + 1)
                loss = loss_func(x_hat @ self._H, self._y)  # to avoid using the solution
                loss.backward()
                optimizer.step()

                if i % 200 == 0:
                    print(
                        "generation:",
                        gen + 1,
                        " batch:",
                        i,
                        "\t MSE loss:",
                        loss.item(),
                    )
            loss_gen.append(loss.item())
        return loss_gen

    def evaluate(
        self,
        solution: Tensor,
        num_itr: int = 10,
        device: torch.device = _device,
    ) -> float:
        """Evaluate function

        Args:
            num_itr (int, optional): Number of iterations choose. Defaults to 10.
            solution (Tensor, optional): The solution of the linear problem. Defaults to None.
            device (torch.device, optional): The device. Defaults to _device.

        Returns:
            torch.Tensor : The error between the exact solution and the proposed solution
        """
        s_hat, _ = self(num_itr)

        err = (torch.norm(solution.to(device) - s_hat.to(device)) ** 2).item() / (
            self.A.shape[0] * self.bs
        )
        return err

class SORNet(UnfoldingNet):
    """Deep unfolded SOR with a constant step size."""

    device: torch.device
    """Device to run the model on."""

    inv_omega: nn.Parameter
    """Inverse of the relaxation parameter omega."""

    def __init__(
        self,
        h: Tensor,
        bs: int,
        y: Tensor,
        init_val_SORNet: float = 1.1,
        device: torch.device = _device,
    ):
        """Initialize the SORNet model.

        Args:
          a: Matrix $A$ of the linear system.
          h: Matrix $H$.
          bs: Batch size.
          y: Solution of the linear equation.
          init_val_SORNet: Initial value for `inv_omega`.
          device: Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__(h, bs, y, device)
        self.inv_omega = nn.Parameter(torch.tensor(init_val_SORNet, device=device))

class SORChebyNet(UnfoldingNet):
    """Deep unfolded SOR with Chebyshev acceleration."""

    device: torch.device
    """Device to run the model on."""

    gamma: nn.Parameter
    """Gamma parameter for each iteration."""

    omega: nn.Parameter
    """Omega parameter for each iteration."""

    inv_omega: nn.Parameter
    """Inverse of the relaxation parameter omega."""

    def __init__(
        self,
        num_itr: int,
        h: Tensor,
        bs: int,
        y: Tensor,
        init_val_SOR_CHEBY_Net_omega: float = 0.6,
        init_val_SOR_CHEBY_Net_gamma: float = 0.8,
        init_val_SOR_CHEBY_Net_alpha: float = 0.9,
        device: torch.device = _device,
    ):
        """Initialize the SOR_CHEBY_Net model.

        Args:
          num_itr: Number of iterations.
          a: Matrix $A$ of the linear system.
          h: Matrix $H$.
          bs: Batch size.
          y: Solution of the linear equation.
          init_val_SOR_CHEBY_Net_omega: Initial value for `omega`.
          init_val_SOR_CHEBY_Net_gamma: Initial value for `gamma`.
          init_val_SOR_CHEBY_Net_alpha: Initial value for `inv_omega`.
          device: Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__(h, bs, y, device)
        self.gamma = nn.Parameter(
            init_val_SOR_CHEBY_Net_gamma * torch.ones(num_itr, device=device)
        )
        self.omega = nn.Parameter(
            init_val_SOR_CHEBY_Net_omega * torch.ones(num_itr, device=device)
        )
        self.inv_omega = nn.Parameter(
            torch.tensor(init_val_SOR_CHEBY_Net_alpha, device=device)
        )

class AORNet(UnfoldingNet):
    """Deep unfolded AOR with a constant step size."""

    device: torch.device
    """Device to run the model on."""

    r: nn.Parameter
    """Parameter `r` for AOR."""

    omega: nn.Parameter
    """Relaxation parameter omega."""

    def __init__(
        self,
        h: Tensor,
        bs: int,
        y: Tensor,
        init_val_AORNet_r: float = 0.9,
        init_val_AORNet_omega: float = 1.5,
        device: torch.device = _device,
    ):
        """Initialize the AORNet model.

        Args:
          a: Matrix $A$ of the linear system.
          h: Matrix $H$.
          bs: Batch size.
          y: Solution of the linear equation.
          init_val_AORNet_r: Initial value for `r`.
          init_val_AORNet_omega: Initial value for `omega`.
          device: Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__(h, bs, y, device)
        self.r = nn.Parameter(torch.tensor(init_val_AORNet_r, device=device))
        self.omega = nn.Parameter(torch.tensor(init_val_AORNet_omega, device=device))

class RichardsonNet(UnfoldingNet):
    """Deep unfolded Richardson iteration."""

    inv_omega: nn.Parameter
    """Inverse of the relaxation parameter omega."""

    def __init__(
        self,
        a: Tensor,
        h: Tensor,
        bs: int,
        y: Tensor,
        init_val_RINet: float = 0.1,
        device: torch.device = _device,
    ):
        """Initialize the RINet model.

        Args:
          a: Matrix $A$ of the linear system.
          h: Matrix $H$.
          bs: Batch size.
          y: Solution of the linear equation.
          init_val_RINet: Initial value for `inv_omega`.
          device: Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__(a, h, bs, y, device)
        self.inv_omega = nn.Parameter(torch.tensor(init_val_RINet, device=device))


# class SORNet(UnfoldingNet):
#     """Deep unfolded SOR with a constant step size."""

#     device: torch.device
#     """Device to run the model on."""

#     inv_omega: nn.Parameter
#     """Inverse of the relaxation parameter omega."""

#     def __init__(
#         self,
#         h: Tensor,
#         bs: int,
#         y: Tensor,
#         init_val_SORNet: float = 1.1,
#         device: torch.device = _device,
#     ):
#         """Initialize the SORNet model.

#         Args:
#           a: Matrix $A$ of the linear system.
#           h: Matrix $H$.
#           bs: Batch size.
#           y: Solution of the linear equation.
#           init_val_SORNet: Initial value for `inv_omega`.
#           device: Device to run the model on ('cpu' or 'cuda').
#         """
#         super().__init__(h, bs, y, device)
#         self.inv_omega = nn.Parameter(torch.tensor(init_val_SORNet, device=device))

#     def forward(self, num_itr: int = 25) -> tuple[Tensor, list[Tensor]]:
#         """Perform forward pass of the SORNet model.

#         Args:
#           num_itr: Number of iterations.

#         Returns:
#           A tuple with the following contents:
#             - Output tensor.
#             - List of intermediate results.
#         """
#         traj = []

#         m_inv = torch.linalg.inv(self.inv_omega * self.D + self.L)
#         s = torch.zeros(self.bs, self.H.size(0), device=self.device)
#         traj.append(s)
#         yMF = torch.matmul(self.y, self.H.T)
#         s = torch.matmul(yMF, self.Dinv)

#         for _ in range(num_itr):
#             temp = torch.matmul(s, (self.inv_omega - 1) * self.D - self.U) + yMF
#             s = torch.matmul(temp, m_inv)
#             traj.append(s)

#         return s, traj


# class SORChebyNet(UnfoldingNet):
#     """Deep unfolded SOR with Chebyshev acceleration."""

#     device: torch.device
#     """Device to run the model on."""

#     gamma: nn.Parameter
#     """Gamma parameter for each iteration."""

#     omega: nn.Parameter
#     """Omega parameter for each iteration."""

#     inv_omega: nn.Parameter
#     """Inverse of the relaxation parameter omega."""

#     def __init__(
#         self,
#         num_itr: int,
#         h: Tensor,
#         bs: int,
#         y: Tensor,
#         init_val_SOR_CHEBY_Net_omega: float = 0.6,
#         init_val_SOR_CHEBY_Net_gamma: float = 0.8,
#         init_val_SOR_CHEBY_Net_alpha: float = 0.9,
#         device: torch.device = _device,
#     ):
#         """Initialize the SOR_CHEBY_Net model.

#         Args:
#           num_itr: Number of iterations.
#           a: Matrix $A$ of the linear system.
#           h: Matrix $H$.
#           bs: Batch size.
#           y: Solution of the linear equation.
#           init_val_SOR_CHEBY_Net_omega: Initial value for `omega`.
#           init_val_SOR_CHEBY_Net_gamma: Initial value for `gamma`.
#           init_val_SOR_CHEBY_Net_alpha: Initial value for `inv_omega`.
#           device: Device to run the model on ('cpu' or 'cuda').
#         """
#         super().__init__(h, bs, y, device)
#         self.gamma = nn.Parameter(
#             init_val_SOR_CHEBY_Net_gamma * torch.ones(num_itr, device=device)
#         )
#         self.omega = nn.Parameter(
#             init_val_SOR_CHEBY_Net_omega * torch.ones(num_itr, device=device)
#         )
#         self.inv_omega = nn.Parameter(
#             torch.tensor(init_val_SOR_CHEBY_Net_alpha, device=device)
#         )

#     def forward(self, num_itr: int = 25) -> tuple[Tensor, list[Tensor]]:
#         """Perform forward pass of the SOR_CHEBY_Net model.

#         Args:
#           num_itr: Number of iterations.

#         Returns:
#           A tuple with the following contents:
#             - Output tensor.
#             - List of intermediate results.
#         """
#         traj = []

#         m_inv = torch.linalg.inv(self.inv_omega * self.D + self.L)
#         s = torch.zeros(self.bs, self.H.size(0), device=self.device)  # modif to size(0)
#         s_new = torch.zeros(
#             self.bs, self.H.size(0), device=self.device
#         )  # modif to size(0)
#         traj.append(s)
#         yMF = torch.matmul(self.y, self.H.T)
#         s = torch.matmul(yMF, self.Dinv)
#         s_present = s
#         s_old = torch.zeros_like(s_present)

#         for i in range(num_itr):
#             temp = torch.matmul(s, (self.inv_omega - 1) * self.D - self.U) + yMF
#             s = torch.matmul(temp, m_inv)

#             s_new = (
#                 self.omega[i] * (self.gamma[i] * (s - s_present) + (s_present - s_old))
#                 + s_old
#             )
#             s_old = s
#             s_present = s_new
#             traj.append(s_new)

#         return s_new, traj


# =====================================================================================


# class AORNet(UnfoldingNet):
#     """Deep unfolded AOR with a constant step size."""

#     device: torch.device
#     """Device to run the model on."""

#     r: nn.Parameter
#     """Parameter `r` for AOR."""

#     omega: nn.Parameter
#     """Relaxation parameter omega."""

#     def __init__(
#         self,
#         h: Tensor,
#         bs: int,
#         y: Tensor,
#         init_val_AORNet_r: float = 0.9,
#         init_val_AORNet_omega: float = 1.5,
#         device: torch.device = _device,
#     ):
#         """Initialize the AORNet model.

#         Args:
#           a: Matrix $A$ of the linear system.
#           h: Matrix $H$.
#           bs: Batch size.
#           y: Solution of the linear equation.
#           init_val_AORNet_r: Initial value for `r`.
#           init_val_AORNet_omega: Initial value for `omega`.
#           device: Device to run the model on ('cpu' or 'cuda').
#         """
#         super().__init__(h, bs, y, device)
#         self.r = nn.Parameter(torch.tensor(init_val_AORNet_r, device=device))
#         self.omega = nn.Parameter(torch.tensor(init_val_AORNet_omega, device=device))

#     def forward(self, num_itr: int = 25) -> tuple[Tensor, list[Tensor]]:
#         """Perform forward pass of the AORNet model.

#         Args:
#           num_itr: Number of iterations.

#         Returns:
#           A tuple with the following contents:
#           - Output tensor.
#           - List of intermediate results.
#         """
#         traj = []

#         m_inv = torch.linalg.inv(self.L - self.r * self.D)
#         n = (
#             (1 - self.omega) * self.D
#             + (self.omega - self.r) * self.L
#             + self.omega * self.U
#         )
#         s = torch.zeros(
#             self.bs, self.H.size(0), device=self.device
#         )  # change to size(0)
#         traj.append(s)
#         yMF = torch.matmul(self.y, self.H.T)
#         s = torch.matmul(yMF, self.Dinv)

#         for _ in range(num_itr):
#             s = torch.matmul(s, torch.matmul(m_inv, n)) + torch.matmul(yMF, m_inv)
#             traj.append(s)

#         return s, traj


# class RichardsonNet(UnfoldingNet):
#     """Deep unfolded Richardson iteration."""

#     inv_omega: nn.Parameter
#     """Inverse of the relaxation parameter omega."""

#     def __init__(
#         self,
#         a: Tensor,
#         h: Tensor,
#         bs: int,
#         y: Tensor,
#         init_val_RINet: float = 0.1,
#         device: torch.device = _device,
#     ):
#         """Initialize the RINet model.

#         Args:
#           a: Matrix $A$ of the linear system.
#           h: Matrix $H$.
#           bs: Batch size.
#           y: Solution of the linear equation.
#           init_val_RINet: Initial value for `inv_omega`.
#           device: Device to run the model on ('cpu' or 'cuda').
#         """
#         super().__init__(a, h, bs, y, device)
#         self.inv_omega = nn.Parameter(torch.tensor(init_val_RINet, device=device))

#     def forward(self, num_itr: int = 25) -> tuple[Tensor, list[Tensor]]:
#         """Perform forward pass of the RINet model.

#         Args:
#           num_itr: Number of iterations.

#         Returns:
#           A tuple with the following contents:
#             - Output tensor.
#             - List of intermediate results.
#         """
#         traj = []

#         s = torch.zeros(self.bs, self.A.shape[0], device=self.device)
#         traj.append(s)
#         yMF = torch.matmul(self.y, self.H.T)
#         s = torch.matmul(yMF, self.Dinv)

#         for _ in range(num_itr):
#             s = s + self.inv_omega * (yMF - torch.matmul(s, self.A))
#             traj.append(s)

#         return s, traj
