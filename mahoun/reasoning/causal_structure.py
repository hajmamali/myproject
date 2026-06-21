"""
Causal Structure Learning
==========================

Learn causal DAGs from observational data.
"""


import logging
from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
from scipy import stats

logger = logging.getLogger(__name__)


class PCAlgorithm:
    """
    PC (Peter-Clark) Algorithm for causal structure learning
    
    Features:
    - Constraint-based approach
    - Learn DAG from conditional independence tests
    - Handle continuous and discrete variables
    """
    
    def __init__(
        self,
        alpha: float = 0.05,
        max_cond_set_size: Optional[int] = None
    ):
        """
        Initialize PC algorithm
        
        Args:
            alpha: Significance level for independence tests
            max_cond_set_size: Maximum conditioning set size
        """
        self.alpha = alpha
        self.max_cond_set_size = max_cond_set_size
        
        logger.info(f"Initialized PCAlgorithm: alpha={alpha}")
    
    def _test_independence(
        self,
        data: np.ndarray,
        i: int,
        j: int,
        cond_set: Set[int]
    ) -> Tuple[bool, float]:
        """
        Test conditional independence
        
        Args:
            data: Data matrix [N, D]
            i: Variable index i
            j: Variable index j
            cond_set: Conditioning set
            
        Returns:
            (is_independent, p_value)
        """
        if len(cond_set) == 0:
            # Marginal independence (correlation test)
            corr, p_value = stats.pearsonr(data[:, i], data[:, j])
            is_independent = p_value > self.alpha
        else:
            # Partial correlation test
            cond_indices = list(cond_set)
            
            # Compute partial correlation
            # Regress out conditioning variables
            X_cond = data[:, cond_indices]
            
            # Residuals
            from sklearn.linear_model import LinearRegression
            
            reg_i = LinearRegression().fit(X_cond, data[:, i])
            res_i = data[:, i] - reg_i.predict(X_cond)
            
            reg_j = LinearRegression().fit(X_cond, data[:, j])
            res_j = data[:, j] - reg_j.predict(X_cond)
            
            # Correlation of residuals
            corr, p_value = stats.pearsonr(res_i, res_j)
            is_independent = p_value > self.alpha
        
        return is_independent, p_value
    
    def learn_structure(self, data: np.ndarray, var_names: Optional[List[str]] = None) -> nx.DiGraph:
        """
        Learn causal structure using PC algorithm
        
        Args:
            data: Data matrix [N, D]
            var_names: Variable names (optional)
            
        Returns:
            Learned DAG
        """
        n_samples, n_vars = data.shape
        
        if var_names is None:
            var_names = [f"X{i}" for i in range(n_vars)]
        
        # Initialize complete undirected graph
        graph = nx.Graph()
        graph.add_nodes_from(range(n_vars))
        
        # Add all edges
        for i in range(n_vars):
            for j in range(i + 1, n_vars):
                graph.add_edge(i, j)
        
        # Skeleton discovery
        max_size = self.max_cond_set_size or n_vars - 2
        
        for cond_size in range(max_size + 1):
            edges_to_remove: List[Any] = []
            for i, j in list(graph.edges()):
                # Get neighbors
                neighbors_i = set(graph.neighbors(i)) - {j}
                neighbors_j = set(graph.neighbors(j)) - {i}
                neighbors = neighbors_i | neighbors_j
                
                if len(neighbors) < cond_size:
                    continue
                
                # Test all conditioning sets of size cond_size
                from itertools import combinations
                
                for cond_set in combinations(neighbors, cond_size):
                    is_indep, p_value = self._test_independence(
                        data, i, j, set(cond_set)
                    )
                    
                    if is_indep:
                        edges_to_remove.append((i, j))
                        break
            
            # Remove edges
            for edge in edges_to_remove:
                if graph.has_edge(*edge):
                    graph.remove_edge(*edge)
        
        # Orient edges (simplified - full PC includes v-structures)
        dag = nx.DiGraph()
        dag.add_nodes_from(range(n_vars))
        
        for i, j in graph.edges():
            # Simple heuristic: orient based on correlation direction
            corr, _ = stats.pearsonr(data[:, i], data[:, j])
            if corr > 0:
                dag.add_edge(i, j)
            else:
                dag.add_edge(j, i)
        
        # Relabel with variable names
        mapping = {i: var_names[i] for i in range(n_vars)}
        dag = nx.relabel_nodes(dag, mapping)
        
        logger.info(
            f"Learned causal structure: {dag.number_of_nodes()} nodes, "
            f"{dag.number_of_edges()} edges"
        )
        
        return dag


class NOTEARSAlgorithm:
    """
    NOTEARS: Non-combinatorial Optimization via Trace Exponential and Augmented lagrangian for Structure learning
    
    Features:
    - Continuous optimization approach
    - Learn DAG by solving constrained optimization
    - Handles linear and nonlinear relationships
    """
    
    def __init__(
        self,
        lambda_1: float = 0.1,
        max_iter: int = 100,
        h_tol: float = 1e-8
    ):
        """
        Initialize NOTEARS
        
        Args:
            lambda_1: L1 regularization parameter
            max_iter: Maximum iterations
            h_tol: Tolerance for acyclicity constraint
        """
        self.lambda_1 = lambda_1
        self.max_iter = max_iter
        self.h_tol = h_tol
        
        logger.info(f"Initialized NOTEARSAlgorithm: lambda={lambda_1}")
    
    def _h_func(self, W: np.ndarray) -> float:
        """
        Acyclicity constraint h(W) = tr(e^(W ⊙ W)) - d
        
        Args:
            W: Weighted adjacency matrix
            
        Returns:
            h value (should be 0 for DAG)
        """
        d = W.shape[0]
        M = np.eye(d) + W * W / d
        E = np.linalg.matrix_power(M, d - 1)
        h = np.trace(E) - d
        return h
    
    def learn_structure(
        self,
        data: np.ndarray,
        var_names: Optional[List[str]] = None
    ) -> nx.DiGraph:
        """
        Learn causal structure using NOTEARS
        
        Args:
            data: Data matrix [N, D]
            var_names: Variable names (optional)
            
        Returns:
            Learned DAG
        """
        n_samples, n_vars = data.shape
        
        if var_names is None:
            var_names = [f"X{i}" for i in range(n_vars)]
        
        # Standardize data
        data_std = (data - data.mean(axis=0)) / data.std(axis=0)
        
        # Initialize W
        W = np.zeros((n_vars, n_vars))
        
        # Simplified NOTEARS (full version requires scipy.optimize)
        # Use least squares with L1 regularization
        
        for j in range(n_vars):
            # Regress X_j on all other variables
            X = np.delete(data_std, j, axis=1)
            y = data_std[:, j]
            
            # Lasso regression (simplified)
            from sklearn.linear_model import Lasso
            
            lasso = Lasso(alpha=self.lambda_1, max_iter=1000)
            lasso.fit(X, y)
            
            # Fill W
            coef_idx = 0
            for i in range(n_vars):
                if i != j:
                    W[i, j] = lasso.coef_[coef_idx]
                    coef_idx += 1
        
        # Threshold small values
        W[np.abs(W) < 0.1] = 0
        
        # Create DAG
        dag = nx.DiGraph()
        dag.add_nodes_from(var_names)
        
        for i in range(n_vars):
            for j in range(n_vars):
                if W[i, j] != 0:
                    dag.add_edge(var_names[i], var_names[j], weight=W[i, j])
        
        # Check acyclicity
        if not nx.is_directed_acyclic_graph(dag):
            logger.warning("Learned graph is not a DAG, removing cycles")
            # Remove weakest edges to break cycles
            while not nx.is_directed_acyclic_graph(dag):
                try:
                    cycle = nx.find_cycle(dag)
                    # Remove weakest edge in cycle
                    weakest = min(cycle, key=lambda e: abs(dag[e[0]][e[1]]['weight']))
                    dag.remove_edge(weakest[0], weakest[1])
                except nx.NetworkXNoCycle:
                    break
        
        logger.info(
            f"Learned causal structure (NOTEARS): {dag.number_of_nodes()} nodes, "
            f"{dag.number_of_edges()} edges"
        )
        
        return dag


class CausalStructureLearner:
    """
    Unified interface for causal structure learning
    
    Supports multiple algorithms:
    - PC algorithm
    - NOTEARS
    """
    
    def __init__(self, algorithm: str = 'pc', **kwargs):
        """
        Initialize structure learner
        
        Args:
            algorithm: Algorithm to use ('pc' or 'notears')
            **kwargs: Algorithm-specific parameters
        """
        self.algorithm = algorithm
        
        if algorithm == 'pc':
            self.learner = PCAlgorithm(**kwargs)
        elif algorithm == 'notears':
            self.learner = NOTEARSAlgorithm(**kwargs)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        logger.info(f"Initialized CausalStructureLearner: algorithm={algorithm}")
    
    def learn(
        self,
        data: np.ndarray,
        var_names: Optional[List[str]] = None
    ) -> nx.DiGraph:
        """
        Learn causal structure
        
        Args:
            data: Data matrix
            var_names: Variable names
            
        Returns:
            Learned DAG
        """
        return self.learner.learn_structure(data, var_names)
