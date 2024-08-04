# Copyright (c) 2023-2024 Salah Berra and contributors
# Distributed under the the GNU General Public License (See accompanying file
# LICENSE or copy at https://www.gnu.org/licenses/)

"""Conventional iterative methods."""

import torch
from numpy.typing import NDArray
from torch import Tensor

from .utils import _decompose_matrix, _device

class IterativeModel:
    """Base model class for matrix decomposition and initialization."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    def __init__(self, n: int, a: NDArray, h: Tensor, bs: int, y: Tensor, device: torch.device=_device):
        """Initialize the base_model with the given parameters and decompose matrix $A$.

        Args:
          n: Dimension of the solution.
          a: Input square matrix to decompose.
          h: Random matrix $H$.
          bs: Batch size.
          y: Solution tensor.
          device: Device to run the model on ('cpu' or 'cuda').
        """
        self.n = n
        self.H = h
        self.bs = bs
        self.y = y

        self.A, self.D, self.L, self.U, self.Dinv, self.Minv = _decompose_matrix(a, device)
    
    def solve(self,
              total_itr: int = 25,
              device: torch.device=_device
          ) -> tuple[list[Tensor], list[float]] :
        """Perform iterations using the provided model and calculate the error norm at each iteration.

      Args:
        total_itr: Total number of iterations to perform.
        device: Device to run the model on ('cpu' or 'cuda').
        
      Returns:
        A tuple with the following contents:
          - List of tensors representing the solution estimates at each iteration.
      """
        s_hats = []

        for i in range(total_itr + 1):
          
            traj = []
            s = torch.zeros(self.bs, self.n).to(device)
            traj.append(s)

            yMF = torch.matmul(self.y, self.H.T)  # Assuming H is defined
            s = torch.matmul(yMF, self.Dinv)  # Generate batch initial solution vector
            
            s_hat, _ = self._iterate(i, traj, yMF, s)
            s_hats.append(s_hat)

        return s_hats

class GaussSeidel(IterativeModel):
    """Class implementing the Gauss-Seidel algorithm for solving a linear system."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    num_itr: int
    """The number of Gauss-Seidel iterations to perform."""

    def __init__(self, n: int, a: NDArray, h: Tensor, bs: int, y: Tensor, device: torch.device=_device):
        """Initialize the Gauss-Seidel solver.

        Args:
          n: Dimension of the solution.
          a: Input square matrix to decompose.
          h: Random matrix H.
          bs: Batch size.
          y: Solution tensor.
          device: Device to run the model on ('cpu' or 'cuda').
        """
        super().__init__(n, a, h, bs, y, device)

    def _iterate(self, num_itr: int = 25, traj:list=None, yMF:torch.tensor=None, s:torch.tensor=None) -> tuple[Tensor, list]:
        """Performs the Gauss-Seidel iterations and returns the final solution
          and trajectory of solutions.

        Args:
          num_itr: The number of iterations to perform.

        Returns:
          A tuple with the following contents:
            - The final solution tensor of shape (`bs`, `n`).
            - List containing the trajectory of solutions throughout the iterations.
        """
        
        for _ in range(num_itr):
            temp = -torch.matmul(s, self.U) + yMF
            s = torch.matmul(temp, self.Minv)
            traj.append(s)

        return s, traj


class Richardson(IterativeModel):
    """Class implementing the Richardson iteration algorithm for solving a linear system."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    def __init__(self, n: int, a: NDArray, h: Tensor, bs: int, y: Tensor, omega: float = 0.25, device: torch.device=_device):
        """Initialize the Richardson iteration solver.

        Args:
          n: Dimension of the solution.
          a: Input square matrix to decompose.
          h: Random matrix $H$.
          bs: Batch size.
          y: Solution tensor.
        """
        super().__init__(n, a, h, bs, y, device)
        
        self.omega = torch.tensor(omega)

    def _iterate(self, num_itr: int = 25, traj:list=None, yMF:torch.tensor=None, s:torch.tensor=None) -> tuple[Tensor, list]:
        """Performs the Richardson iterations and returns the final solution and
          trajectory of solutions.

        Args:
          num_itr: The number of iterations to perform.

        Returns:
          A tuple with the following contents:
            - The final solution tensor of shape (`bs`, `n`).
            - List containing the trajectory of solutions throughout the iterations.
        """

        for _ in range(num_itr):
            s = s + torch.mul(self.omega, (yMF - torch.matmul(s, self.A)))
            traj.append(s)

        return s, traj


class Jacobi(IterativeModel):
    """Class implementing the Jacobi iteration algorithm for solving a linear system."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    omega: Tensor
    """Relaxation parameter for Jacobi iterations."""

    def __init__(
        self,
        n: int,
        a: NDArray,
        h: Tensor,
        bs: int,
        y: Tensor,
        omega: float = 0.2,
        device: torch.device=_device
    ):
        """Initialize the Jacobi iteration solver.

        Args:
          n: Dimension of the solution.
          a: Input square matrix to decompose.
          h: Random matrix $H$.
          bs: Batch size.
          y: Solution tensor.
          omega: Relaxation parameter for Jacobi iterations.
        """
        super().__init__(n, a, h, bs, y, device)
        self.omega = torch.tensor(omega)

    def _iterate(self, num_itr: int = 25, traj:list=None, yMF:torch.tensor=None, s:torch.tensor=None) -> tuple[Tensor, list]:
        """Performs the Jacobi iterations and returns the final solution and
          trajectory of solutions.

        Args:
          num_itr: The number of iterations to perform.

        Returns:
          A tuple with the following contents:
            - The final solution tensor of shape (`bs`, `n`).
            - List containing the trajectory of solutions throughout the iterations.
        """

        for _ in range(num_itr):
            temp = torch.matmul(self.Dinv, (self.D - self.A))
            s = torch.matmul(s, temp) + torch.matmul(yMF, self.Dinv)
            traj.append(s)

        return s, traj


class SOR(IterativeModel):
    """Class implementing the Successive Over-Relaxation (SOR) algorithm for
    solving a linear system."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    omega: Tensor
    """Relaxation parameter for SOR iterations."""

    def __init__(
        self,
        n: int,
        a: NDArray,
        h: Tensor,
        bs: int,
        y: Tensor,
        omega: float = 1.8,
        device: torch.device=_device
    ):
        """Initialize the SOR solver.

        Args:
          n: Dimension of the solution.
          A: Input square matrix to decompose.
          H: Random matrix $H$.
          bs: Batch size.
          y: Solution tensor.
          omega: Relaxation parameter for SOR iterations.
        """
        super().__init__(n, a, h, bs, y, device)
        self.omega = torch.tensor(omega)

    def _iterate(self, num_itr: int = 25, traj:list=None, yMF:torch.tensor=None, s:torch.tensor=None) -> tuple[Tensor, list]:
        """Performs the SOR iterations and returns the final solution and
          trajectory of solutions.

        Args:
          num_itr: The number of iterations to perform.

        Returns:
          A tuple with the following contents:
            - The final solution tensor of shape (`bs`, `n`).
            - List containing the trajectory of solutions throughout the iterations.
        """

        inv_omega = torch.div(1, self.omega)
        m_inv_sor = torch.linalg.inv(self.D - torch.mul(inv_omega, self.L))

        for _ in range(num_itr):
            temp = torch.mul((inv_omega - 1), self.D) + torch.mul(inv_omega, self.U)
            s = torch.matmul(s, torch.matmul(m_inv_sor, temp)) + torch.matmul(
                yMF, m_inv_sor
            )
            traj.append(s)

        return s, traj


class SORCheby(IterativeModel):
    """Class implementing the SOR-Chebyshev algorithm for solving a linear system."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    omega: Tensor
    """Relaxation parameter for SOR iterations."""

    omegaa: Tensor
    """Acceleration parameter for SOR-Chebyshev iterations."""

    gamma: Tensor
    """Damping factor for SOR-Chebyshev iterations."""

    def __init__(
        self,
        n: int,
        a: NDArray,
        h: Tensor,
        bs: int,
        y: Tensor,
        omega: float = 1.8,
        omegaa: float = 0.8,
        gamma: float = 0.8,
        device: torch.device=_device
    ):
        """Initialize the SOR-Chebyshev solver.

        Args:
          n: Dimension of the solution.
          a: Input square matrix to decompose.
          h: Random matrix $H$.
          bs: Batch size.
          y: Solution tensor.
          omega: Relaxation parameter for SOR iterations.
          omegaa: Acceleration parameter for SOR-Chebyshev iterations.
          gamma: Damping factor for SOR-Chebyshev iterations.
        """
        super().__init__(n, a, h, bs, y, device)
        self.omega = torch.tensor(omega)
        self.omegaa = torch.tensor(omegaa)
        self.gamma = torch.tensor(gamma)

    def _iterate(self, num_itr: int = 25, traj:list=None, yMF:torch.tensor=None, s:torch.tensor=None) -> tuple[Tensor, list]:
        """Performs the SOR-Chebyshev iterations and returns the final solution
          and trajectory of solutions.

        Args:
          num_itr: The number of iterations to perform.

        Returns:
          A tuple with the following contents:
            - The final solution tensor of shape (`bs`, `n`).
            - List containing the trajectory of solutions throughout the iterations.
        """

        inv_omega = torch.div(1, self.omega)
        m_inv_sor = torch.linalg.inv(self.D - torch.mul(inv_omega, self.L))

        s_present = s
        s_old = torch.zeros(s_present.shape)

        for _ in range(num_itr):
            temp = torch.mul((inv_omega - 1), self.D) + torch.mul(inv_omega, self.U)
            s = torch.matmul(s, torch.matmul(m_inv_sor, temp)) + torch.matmul(
                yMF, m_inv_sor
            )

            s_new = (
                self.omegaa * (self.gamma * (s - s_present) + (s_present - s_old))
                + s_old
            )
            s_old = s
            s_present = s_new

            traj.append(s_new)

        return s_new, traj


class AOR(IterativeModel):
    """Class implementing the Accelerated Over-Relaxation (AOR) algorithm for
    solving a linear system."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    omega: Tensor
    """Relaxation parameter for AOR iterations."""

    r: Tensor
    """Relaxation parameter."""

    def __init__(
        self,
        n: int,
        a: NDArray,
        h: Tensor,
        bs: int,
        y: Tensor,
        omega: float = 0.3,
        r: float = 0.2,
        device: torch.device=_device
    ):
        """Initialize the AOR solver.

        Args:
          n: Dimension of the solution.
          a: Input square matrix to decompose.
          h: Random matrix $H$.
          bs: Batch size.
          y: Solution tensor.
          omega: Relaxation parameter for AOR iterations.
          r: Relaxation parameter.
        """
        super().__init__(n, a, h, bs, y, device)
        self.omega = torch.tensor(omega)
        self.r = torch.tensor(r)

    def _iterate(self, num_itr: int = 25, traj:list=None, yMF:torch.tensor=None, s:torch.tensor=None) -> tuple[Tensor, list]:
        """Performs the AOR iterations and returns the final solution and
          trajectory of solutions.

        Args:
          num_itr: The number of iterations to perform.

        Returns:
          A tuple with the following contents:
            - The final solution tensor of shape (`bs`, `n`).
            - List containing the trajectory of solutions throughout the iterations.
        """

        m = self.D - torch.mul(self.r, self.L)
        m_inv_aor = torch.linalg.inv(m)
        
        # ! bug : difference between n and self.n (some ambiguity)
        n = (
            torch.mul((1 - self.omega), self.D)
            + torch.mul((self.omega - self.r), self.L)
            + torch.mul(self.omega, self.U)
        )

        for _ in range(num_itr):
            s = torch.matmul(s, torch.matmul(m_inv_aor, n)) + torch.mul(
                self.omega, torch.matmul(yMF, m_inv_aor)
            )
            traj.append(s)

        return s, traj


class AORCheby(IterativeModel):
    """Class implementing the Accelerated Over-Relaxation (AOR) with Chebyshev
    acceleration algorithm for solving a linear system."""

    n: int
    """Dimension of the solution."""

    H: Tensor
    """Random matrix $H$."""

    bs: int
    """Batch size."""

    y: Tensor
    """Solution tensor."""

    A: Tensor
    """Original matrix converted to a torch tensor."""

    D: Tensor
    """Diagonal matrix of $A$."""

    L: Tensor
    """Lower triangular matrix of $A$."""

    U: Tensor
    """Upper triangular matrix of $A$."""

    Dinv: Tensor
    """Inverse of the diagonal matrix $D$."""

    Minv: Tensor
    """Inverse of the matrix $D + L$."""

    omega: Tensor
    """Relaxation parameter for AOR iterations."""

    r: Tensor
    """Relaxation parameter."""

    def __init__(
        self,
        n: int,
        a: NDArray,
        h: Tensor,
        bs: int,
        y: Tensor,
        omega: float = 0.1,
        r: float = 0.1,
        device: torch.device=_device
    ):
        """Initialize the AOR-Chebyshev solver.

        Args:
          n: Dimension of the solution.
          a: Input square matrix to decompose.
          h: Random matrix $H$.
          bs: Batch size.
          y: Solution tensor.
          omega: Relaxation parameter for AOR iterations.
          r: Relaxation parameter.
        """
        super().__init__(n, a, h, bs, y, device)
        self.omega = torch.tensor(omega)
        self.r = torch.tensor(r)

    def _iterate(self, num_itr: int = 25, traj:list=None, yMF:torch.tensor=None, s:torch.tensor=None) -> tuple[Tensor, list]:
        """Performs the AOR-Chebyshev iterations and returns the final solution
          and trajectory of solutions.

        Args:
          num_itr: The number of iterations to perform.

        Returns:
          A tuple with the following contents:
            - The final solution tensor of shape (`bs`, `n`).
            - List containing the trajectory of solutions throughout the iterations.
        """

        y0 = s

        m = self.D - torch.mul(self.r, self.L)
        m_inv = torch.linalg.inv(m)
        n = (
            torch.mul((1 - self.omega), self.D)
            + torch.mul((self.omega - self.r), self.L)
            + torch.mul(self.omega, self.U)
        )
        temp = torch.matmul(m_inv, n)

        rho = torch.tensor(0.1)
        mu0 = torch.tensor(1)
        mu1 = rho
        xhat1 = torch.matmul(s, temp) + self.omega * torch.matmul(yMF, m_inv)
        y1 = xhat1
        y = y1

        for _ in range(num_itr):
            f = 2 / (rho * mu1)
            j = 1 / mu0
            c = f - j
            mu = 1 / c
            a = (2 * mu) / (rho * mu1)
            y = (
                torch.matmul((y1 * a), torch.matmul(m_inv, n))
                - (((mu / mu0)) * y0)
                + (a * torch.matmul(yMF, m_inv))
            )
            y0 = y1
            y1 = y
            mu0 = mu1
            mu1 = mu

            traj.append(y)

        return y, traj
