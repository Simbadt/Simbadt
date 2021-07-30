import importlib
import pickle
import argparse
from pathlib import Path
from typing import Callable

import yaml
import time
import random
from loguru import logger

from bitcoin.models import Block, Miner
from sim.base_models import Node
from sim.util import Region
from bitcoin.tx_modelings import *
from bitcoin.mining_strategies import *
from bitcoin.consensus import *


class Simulation:
    def __init__(self, config_file=None):
        self.name = ""
        self.results_dir = ""
        self.log_level = "SUCCESS"
        self.sim_reps = 1
        self.sim_iters = 1
        self.iter_seconds = 0.1
        self.block_int_iters = 6000
        self.max_block_size = 10 ** 6
        self.connections_per_node = 2
        self.nodes_in_each_region = -1
        self.set_log_level(self.log_level)
        self.config_file = config_file
        self.dynamic = False
        self.block_reward = 100

        self.nodes = []
        self.connection_predicate: Callable[[Node, Node], bool] = None

    def run(self, report_time=False):
        if self.config_file is not None:
            self.__load_config_file(detailed=False)

        iter_seconds = self.iter_seconds
        logger.warning(f'Simulation {self.name} ({self.sim_iters} iterations).')
        logger.warning('Started simulation.')
        for rep in range(self.sim_reps):
            if self.config_file is not None:
                self.__load_config_file(detailed=True)
            else:
                [node.reset() for node in self.nodes]
                for idx, n1 in enumerate(self.nodes):
                    for n2 in self.nodes[:idx] + self.nodes[idx + 1:]:
                        if self.connection_predicate(n1, n2):
                            n1.connect(n2)
                            n2.connect(n1)
                self.__setup_mining()

            start_time = time.time()
            sim_name = f'{self.name}_{rep}'
            for i in range(1, self.sim_iters):
                [node.step(iter_seconds) for node in self.nodes]
            end_time = time.time()

            if report_time:
                print(f'Total simulation time (s):\t{end_time - start_time}')
                print(f'Average time per step (s):\t{(end_time - start_time) / self.sim_iters}')

            logger.warning('Finished simulation. Saving nodes...')
            Path(f'{self.results_dir}/{sim_name}').mkdir(parents=True, exist_ok=True)
            for node in self.nodes:
                with open(f'{self.results_dir}/{sim_name}/{node.name}', 'wb+') as f:
                    pickle.dump(node, f)
            logger.warning(
                f'Simulation {sim_name} complete. Dumped nodes to {self.results_dir}/{sim_name}. Have a good day!')

    def add_node(self, node: Node):
        self.nodes.append(node)

    def __setup_mining(self):
        """Adds genesis block and sets up nodes' consensus oracles"""
        pow_oracle = PoWOracle(self.nodes, self.block_int_iters, self.block_reward)
        genesis_block = Block(Miner('satoshi', 0, None, 1), None, 0)
        for node in self.nodes:
            node.consensus_oracle = pow_oracle
            node.save_block(genesis_block)

    def __load_config_file(self, detailed=False):
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
            self.name = config['sim_name']
            self.results_dir = config['results_directory']
            self.sim_reps = config['sim_reps']
            self.sim_iters = config['sim_iters']
            self.iter_seconds = config['iter_seconds']
            self.tx_per_node_per_iter = config['tx_per_node_per_iter']
            self.block_int_iters = config['block_int_iters']
            self.max_block_size = config['max_block_size']
            self.tx_modeling = config['tx_modeling'] + 'TxModel'
            self.nodes_in_each_region = config['nodes_in_each_region']
            self.connections_per_node = config['connections_per_node']
            self.dynamic = config['dynamic_difficulty']
            self.block_reward = config['block_reward']
            self.set_log_level(config['log_level'])

            if detailed:
                TxModelClass = getattr(importlib.import_module('bitcoin.tx_modelings'), self.tx_modeling)
                tx_modeling = TxModelClass()
                mine_strategy = HonestMining()
                logger.warning('Creating nodes...')
                self.nodes = []
                for node in config['nodes']:
                    num_nodes = node['count'] if self.nodes_in_each_region == -1 else self.nodes_in_each_region
                    mine_power = node['region_mine_power'] / num_nodes
                    region = node['region']
                    for idx in range(num_nodes):
                        node = Miner(f'MINER_{region}_{idx}', mine_power, Region(region), self.iter_seconds)
                        node.tx_model = tx_modeling
                        node.mine_strategy = mine_strategy
                        node.tx_per_iter = self.tx_per_node_per_iter
                        node.max_block_size = self.max_block_size
                        self.nodes.append(node)
                self.__setup_mining()

                logger.warning('Setting up random P2P network...')
                for node in self.nodes:
                    node_index = self.nodes.index(node)
                    first_part = self.nodes[:node_index]
                    second_part = self.nodes[node_index + 1:]
                    for i in range(self.connections_per_node):
                        n2 = random.choice(first_part + second_part)
                        node.connect(n2)
                        n2.connect(node)

    @staticmethod
    def set_log_level(level: str):
        logger.remove()
        logger.add(sys.stdout, level=level)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blockchain simulator.")
    parser.add_argument('-c', metavar='filename', default='config.yaml',
                        help='Name of the YAML configuration file (default: config.yaml)')
    parser.add_argument('-s', metavar='seed', type=int, help='Seed for random number generation')
    args = parser.parse_args()
    config_name = args.c
    seed = args.s

    if config_name[-5:] != '.yaml':
        print('Please provide a YAML file for configuration.')
        exit()
    if seed is not None:
        random.seed(seed)
    sim = Simulation(config_name)
    sim.run(report_time=True)
