import json
from pathlib import Path

import sc2
from sc2.constants import *


class MyBot(sc2.BotAI):
    with open(Path(__file__).parent / "../botinfo.json") as f:
        NAME = json.load(f)["name"]

    def __init__(self):
        self.army_spread = 4
        self.attacking_army = None
        self.warpgate_started = False

    @property
    def nexus_count(self):
        return self.units(NEXUS).amount

    @property
    def gateway_count(self):
        return self.units(GATEWAY).amount

    async def on_step(self, iteration):
        if iteration == 0:
            await self.chat_send(f"Name: {self.NAME}")
        if self.units(PROBE).amount < 16 * self.nexus_count:
            await self.build_probes()
        if self.supply_left <= 2 * self.gateway_count and not self.already_pending(PYLON):
            await self.build_pylons()
        if self.nexus_count < 2:
            await self.build_expansion()
        await self.build_warpgate_tech()
        await self.build_army()
        await self.distribute_workers()
        await self.build_economy()
        await self.attack_enemy()

    async def build_warpgate_tech(self):
        need_ccore = not self.units(CYBERNETICSCORE).ready.exists and not self.already_pending(CYBERNETICSCORE) 
        ccore_reqs = self.units(PYLON).ready.exists and self.units(GATEWAY).ready.exists
        if need_ccore and ccore_reqs and self.can_afford(CYBERNETICSCORE):
            nexus = self.units(NEXUS).first
            await self.build(CYBERNETICSCORE, nexus, max_distance=20) 

        ccore = self.units(CYBERNETICSCORE).ready
        if ccore.exists and self.can_afford(RESEARCH_WARPGATE) and not self.warpgate_started:
            c = self.units(CYBERNETICSCORE).ready.first
            await self.do(c(RESEARCH_WARPGATE))
        
        for gateway in self.units(GATEWAY).ready:
            abilities = await self.get_available_abilities(gateway)
            if AbilityId.MORPH_WARPGATE in abilities and self.can_afford(AbilityId.MORPH_WARPGATE):
                await self.do(gateway(MORPH_WARPGATE))

    async def build_probes(self):
        for nexus in self.units(NEXUS).ready.noqueue:
            if self.can_afford(PROBE):
                await self.do(nexus.train(PROBE))

    async def build_pylons(self):
        nexus = self.units(NEXUS).first
        if self.can_afford(PYLON):
            await self.build(UnitTypeId.PYLON, nexus.position.towards(self.game_info.map_center, 10))

    async def build_gateway(self):
        nexus = self.units(NEXUS).first
        if self.can_afford(GATEWAY):
            await self.build(GATEWAY, nexus, max_distance=50)

    async def build_economy(self):
        if self.units(GATEWAY).amount < 4 and not self.already_pending(GATEWAY):
            await self.build_gateway()

    async def build_army(self):
        if self.units(NEXUS).amount < 2:
            pass
        for gateway in self.units(GATEWAY).ready.noqueue:
            if self.can_afford(ZEALOT):
                await self.do(gateway.train(ZEALOT))

    async def build_expansion(self):
        if self.can_afford(NEXUS):
            location = await self.get_next_expansion()
            await self.build(NEXUS, near=location)

    async def attack_enemy(self):
        wanted_army_size = 30
        if self.units(UnitTypeId.ZEALOT).amount > wanted_army_size:
            if not self.attacking_army:
                self.attacking_army = self.units(UnitTypeId.ZEALOT).take(wanted_army_size)
            if self.army_spread < 30:
                await self.chat_send(f'Attacking. Army spread {self.army_spread}')
                for zealot in self.attacking_army:
                    await self.do(zealot.attack(self.enemy_start_locations[0]))
                self.attacking_army = None
            else:
                spread_sum = 0
                for i, zealot in enumerate(self.attacking_army):
                    if i == 0:
                        continue
                    spread_sum += zealot.distance_to(self.attacking_army[i-1])
                self.army_spread = spread_sum / wanted_army_size
                await self.do(zealot.move(self.enemy_start_locations[0].towards(self.game_info.map_center, 50)))

