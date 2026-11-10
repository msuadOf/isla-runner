"""静态优先级、平滑加权轮询与任务半数线程门槛。调用者持有事务锁。"""

class QoS:
    def __init__(self, nodes):
        self.nodes = {n['name']: dict(n, reserved=0, credit=0, online=True,
                                     external=n.get('external_cores', 0)) for n in nodes}
        self.leases = {}

    def reserve(self, lease, cores):
        if cores <= 0 or lease in self.leases:
            raise ValueError('非法需求或重复预约')
        threshold = max(1, cores // 2)
        eligible = [n for n in self.nodes.values() if n['online'] and cores <= n['cpus']
                    and n['cpus'] - n.get('external', 0) - n['reserved'] >= threshold]
        if not eligible:
            return None
        priority = max(n['priority'] for n in eligible)
        peers = [n for n in eligible if n['priority'] == priority]
        for node in peers:
            node['credit'] += node['weight']
        chosen = max(peers, key=lambda n: n['credit'])
        chosen['credit'] -= sum(n['weight'] for n in peers)
        chosen['reserved'] += cores
        self.leases[lease] = (chosen['name'], cores)
        return chosen['name']

    def release(self, lease):
        reservation = self.leases.pop(lease, None)
        if reservation is not None:
            name, cores = reservation
            self.nodes[name]['reserved'] -= cores

    def possible(self, cores):
        return any(cores <= n['cpus'] for n in self.nodes.values())
