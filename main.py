import random
from omegaconf import DictConfig, OmegaConf
import hydra
import pickle
from typing import List
from pathlib import Path
import time
import matplotlib.pyplot as plt

from bitcoin.models import Block, Miner
from sim.util import Region


@hydra.main(config_name="config")
def main(cfg: DictConfig) -> List[Miner]:
    # TIMER metrics
    iter_times = []

    links, nodes = [], []

    setup_start = time.time()
    for elt in cfg.nodes:
        nodes_in_region = 1
        # nodes_in_region = elt.count
        mine_power = elt.region_mine_power / nodes_in_region  # FIXME
        for idx in range(nodes_in_region):  # FIXME
            nodes.append(Miner(f'MINER_{elt.region}_{idx}', 0, 0, mine_power, Region(elt.region)))

    genesis_block = Block('satoshi', 'satoshi', 0, 0, None)
    total_mine_power = sum([miner.mine_power for miner in nodes])
    difficulty = 1 / (cfg.block_int_iters * total_mine_power)

    for node in nodes:
        node.difficulty = difficulty
        node.add_block(genesis_block)
        node_index = nodes.index(node)
        first_part = nodes[:node_index]
        second_part = nodes[node_index + 1:]
        for i in range(cfg.connections_per_node):
            n2 = random.choice(first_part + second_part)
            links += node.connect(n2) + n2.connect(node)
    setup_end = time.time()
    setup_time = setup_end - setup_start

    sim_start = time.time()
    for i in range(1, cfg.simulation_iters):
        iter_start = time.time()
        for node in nodes:
            node.step(cfg.iter_seconds)
        iter_end = time.time()
        iter_times.append(iter_end - iter_start)
    sim_end = time.time()
    total_sim_time = sim_end - sim_start

    Path(f'../../../dumps/{cfg.sim_name}').mkdir(parents=True, exist_ok=True)
    for node in nodes:
        node.log_blockchain()
        with open(f'../../../dumps/{cfg.sim_name}/{node.name}', 'wb+') as f:
            pickle.dump(node, f)

    print(f'Times (seconds):')
    print(f'\tSetup time: {round(setup_time, 5)}')
    print(f'\tTotal sim time: {round(total_sim_time, 5)}')
    print(f'\tAvg per iter: {round(sum(iter_times) / len(iter_times), 5)}')
    print(f'\tAvg per node: {round(sum(iter_times) / (len(iter_times) * len(nodes)), 7)}')
    plt.bar(range(len(iter_times)), iter_times)
    plt.xlabel('Iteration')
    plt.ylabel('Time per iteration')
    plt.show()


main()

# plt.plot(active_links)
# plt.axhline(len(links), color='red')
# plt.title('Number of active links')
# plt.show()

# VISUALIZE NETWORK
# if NODE_COUNT <= 100:
#     G = nx.DiGraph()
#     for node in nodes:
#         G.add_node(node, pos=(node.pos.x, node.pos.y))
#     for node in nodes:
#         for link in node.outs:
#             G.add_edge(node, link.end)
#     # fig, ax = plt.subplots()
#     fig = plt.figure(figsize=(500, 500))
#     nx.draw_networkx_nodes(G, nx.get_node_attributes(G, 'pos'))
#     nx.draw_networkx_edges(G, nx.get_node_attributes(G, 'pos'),
#                            connectionstyle="arc3,rad=0.25")
#     plt.show()

# VISUALIZE CHAINS
# miner = nodes[0]
# G = nx.DiGraph()
# for idx, block in enumerate(miner.blockchain.values()):
#     G.add_node(block, pos=(idx, 0))
# for idx, block in enumerate(miner.blockchain.values()):
#     parent = miner.blockchain.get(block.prev_id, None)
#     if parent is not None:
#         G.add_edge(block, parent)
# fig, ax = plt.subplots()
# nx.draw_networkx_nodes(G, nx.get_node_attributes(G, 'pos'))
# nx.draw_networkx_edges(G, nx.get_node_attributes(G, 'pos'),
#                        connectionstyle="arc3,rad=0.25")
# plt.show()
