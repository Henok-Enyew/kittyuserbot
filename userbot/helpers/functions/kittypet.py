# Kitty — a virtual cat whose life follows yours. Pure logic, no Telegram calls,
# so it can be tested offline. plugins/kitty.py stores it and feeds it signals.
#
# Stats (0-100):
#   food    — LeetCode problems are its food: every new accepted problem = a fish.
#             Drops ~4/hour, so a day without solving leaves it hungry.
#   joy     — pets, treats, solves and streak milestones. Drops ~1.5/hour.
#   energy  — sleeps at night and while you're offline; drained by 2-5 AM sessions.
#
# Growth: XP from solves, streak days and care -> level. Stage needs both age
# and level, so a neglected kitten grows up slower:
#   kitten -> young -> adult (collar & bell) -> legend (crown)
#
# Kitty never dies; at worst it is starving and sulking until you come back.
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Tuple

from .kittylife import Signals

COATS = ("orange", "black", "white", "gray", "calico", "siamese")
FOOD_DECAY = 4.0  # per hour
JOY_DECAY = 1.5
ENERGY_DECAY = 3.0  # per awake hour
ENERGY_SLEEP = 12.0  # per sleeping hour
ENERGY_NAP = 6.0  # per hour of daytime nap
NAP_BELOW = 10.0  # Kitty naps when energy is this low
TREAT_COOLDOWN = 3 * 3600
TREATS_PER_DAY = 3
PET_COOLDOWN = 10 * 60
VISITOR_COOLDOWN = 30 * 60
STREAK_MILESTONES = (3, 7, 14, 30, 50, 75, 100, 150, 200, 365, 500, 1000)

STAGES = (  # (name, min age in days, min level)
    ("kitten", 0, 1),
    ("young", 14, 4),
    ("adult", 60, 8),
    ("legend", 180, 15),
)

MOODS = {
    # mood: (emoji, line). {name} {streak} {solved} {time} get filled in.
    "keyboard": ("⌨️", "{name} fell asleep on your keyboard. It's {time}. Go to bed."),
    "asleep": ("💤", "{name} is curled up asleep."),
    "sulking": ("😾", "{name} is sulking: you broke the {lost}-day streak."),
    "starving": ("🙀", "{name} is starving. It eats LeetCode problems, feed it one."),
    "hungry": ("🐟", "{name} is hungry. A LeetCode problem would be nice."),
    "party": ("🎉", "{name} is throwing a party: {streak}-day streak!"),
    "happy": ("😻", "{name} is purring. You solved {solved} today."),
    "rainy": ("🌧", "{name} is watching the rain from the window."),
    "bored": ("😿", "{name} is bored. Give it a pet."),
    "content": ("😺", "{name} is chilling."),
}


def level_for(xp: float) -> int:
    """40 XP for level 2, 160 for 3, 360 for 4 ... (quadratic)."""
    return 1 + int((max(xp, 0) / 40) ** 0.5)


def xp_for_level(level: int) -> int:
    return 40 * (level - 1) ** 2


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


@dataclass
class Kitty:
    name: str = "Kitty"
    coat: str = "orange"
    born: float = field(default_factory=time.time)
    enabled: bool = True
    public: bool = False  # friends in groups can .pet / .feed
    notify: bool = True  # Saved Messages notes for level-ups, milestones, hunger
    food: float = 70.0
    joy: float = 70.0
    energy: float = 80.0
    xp: float = 0.0
    updated: float = field(default_factory=time.time)
    # bookkeeping
    seen_solves: List[str] = field(default_factory=list)  # "YYYY-MM-DD|title" already eaten
    solve_days: List[str] = field(default_factory=list)  # dates you solved (backup for streak)
    last_streak: int = 0
    best_streak: int = 0
    lost_streak: int = 0  # streak that was broken, while sulking
    sulk_until: float = 0.0
    party_until: float = 0.0
    celebrated: List[int] = field(default_factory=list)  # milestones already celebrated
    last_treat: float = 0.0
    treats_day: str = ""
    treats_used: int = 0
    last_pet: float = 0.0
    hungry_note_day: str = ""
    owl_note_day: str = ""
    totals: dict = field(default_factory=lambda: {"fish": 0, "pets": 0, "visitor_pets": 0,
                                                  "treats": 0, "owl_nights": 0})
    last_visitor: str = ""
    mood: str = "content"
    stage_seen: str = "kitten"
    level_seen: int = 1

    # ------------------------------------------------------------------ #
    # storage
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "Kitty":
        if not d:
            return cls()
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        kitty = cls(**known)
        if kitty.coat not in COATS:
            kitty.coat = "orange"
        return kitty

    def to_dict(self) -> dict:
        return asdict(self)

    # ------------------------------------------------------------------ #
    # derived
    # ------------------------------------------------------------------ #

    @property
    def age_days(self) -> int:
        return max(0, int((time.time() - self.born) // 86400))

    @property
    def level(self) -> int:
        return level_for(self.xp)

    @property
    def stage(self) -> str:
        name = STAGES[0][0]
        for stage, min_age, min_level in STAGES:
            if self.age_days >= min_age and self.level >= min_level:
                name = stage
        return name

    def mood_line(self, signals: Optional[Signals] = None) -> Tuple[str, str]:
        emoji, line = MOODS.get(self.mood, MOODS["content"])
        lc = signals.leetcode if signals else None
        t = signals.now.strftime("%H:%M") if signals else ""
        return emoji, line.format(name=self.name, streak=lc.streak if lc else self.last_streak,
                                  solved=lc.solved_today if lc else 0, time=t, lost=self.lost_streak)

    # ------------------------------------------------------------------ #
    # simulation
    # ------------------------------------------------------------------ #

    def advance(self, signals: Signals, now: Optional[float] = None) -> List[str]:
        """Move time forward to `now` using live signals. Returns event notes
        (level-ups, milestones...) worth telling you about."""
        now = now or time.time()
        notes: List[str] = []
        hours = max(0.0, min((now - self.updated) / 3600, 72.0))  # cap catch-up after long downtime
        self.updated = now
        local = signals.now
        sleeping_hours = local.hour < 7 or local.hour >= 23
        resting = (not signals.presence.awake) and sleeping_hours

        # decay / recovery
        self.food = _clamp(self.food - FOOD_DECAY * hours)
        self.joy = _clamp(self.joy - JOY_DECAY * hours)
        # Energy follows what you're doing *now*, so only the last hour uses the live
        # rate; a longer gap (bot downtime) just drifts back towards normal.
        live = min(hours, 1.0)
        gap = hours - live
        if gap:
            self.energy += (70 - self.energy) * min(gap / 8, 1.0)
        if resting:
            rate = ENERGY_SLEEP  # you're offline at night: Kitty sleeps too
        elif signals.night_owl:
            rate = -ENERGY_DECAY * 2  # 2-5 AM sessions wear it out
        elif self.energy < NAP_BELOW or not signals.presence.awake:
            rate = ENERGY_NAP  # daytime cat nap
        else:
            rate = -ENERGY_DECAY / 2
        self.energy = _clamp(self.energy + rate * live)

        notes += self._eat_solves(signals)
        notes += self._track_streak(signals, now)
        notes += self._night_owl(signals)
        self.mood = self._pick_mood(signals, now, resting)
        notes += self._hunger_note(signals)
        notes += self._growth_notes()
        return notes

    def _eat_solves(self, signals: Signals) -> List[str]:
        lc = signals.leetcode
        if not lc.ok:
            return []
        day = lc.day if lc.solved_today else None
        new = []
        for title in lc.titles:
            key = f"{day}|{title}"
            if day and key not in self.seen_solves:
                self.seen_solves.append(key)
                new.append(title)
        self.seen_solves = self.seen_solves[-80:]
        if day and day not in self.solve_days:
            self.solve_days = (self.solve_days + [day])[-400:]
        for _ in new:
            self.food = _clamp(self.food + 35)
            self.joy = _clamp(self.joy + 8)
            self.xp += 25
            self.totals["fish"] = self.totals.get("fish", 0) + 1
        if new:
            first = new[0] if len(new) == 1 else f"{len(new)} problems"
            return [f"🐟 {self.name} ate a fish: you solved {first}."]
        return []

    def _track_streak(self, signals: Signals, now: float) -> List[str]:
        lc = signals.leetcode
        if not lc.ok:
            return []
        notes = []
        streak = lc.streak
        if streak < self.last_streak and not lc.full:
            return []  # partial data (calendar down): don't trust a drop, keep the old streak
        if streak < self.last_streak and self.last_streak >= 2 and streak <= 1:
            self.lost_streak = self.last_streak
            self.sulk_until = now + 18 * 3600
            self.joy = _clamp(self.joy - 30)
            self.celebrated = []
            notes.append(f"😾 {self.name} is sulking: the {self.last_streak}-day LeetCode streak is gone.")
        if streak > self.last_streak:
            self.xp += 5 * min(streak, 10)  # daily streak bonus
            self.sulk_until = 0.0
        self.last_streak = streak
        self.best_streak = max(self.best_streak, streak)
        for m in STREAK_MILESTONES:
            if streak >= m and m not in self.celebrated:
                self.celebrated.append(m)
                if streak == m:  # only throw a party when the milestone is reached, not on catch-up
                    self.party_until = now + 12 * 3600
                    self.joy = _clamp(self.joy + 25)
                    self.xp += m
                    notes.append(f"🎉 {m}-day LeetCode streak! {self.name} is throwing a party.")
        return notes

    def _night_owl(self, signals: Signals) -> List[str]:
        if not signals.night_owl:
            return []
        day = signals.now.date().isoformat()
        if self.owl_note_day == day:
            return []
        self.owl_note_day = day
        self.totals["owl_nights"] = self.totals.get("owl_nights", 0) + 1
        self.joy = _clamp(self.joy - 5)
        return [f"⌨️ It's {signals.now:%H:%M}. {self.name} fell asleep on your keyboard waiting for you."]

    def _pick_mood(self, signals: Signals, now: float, resting: bool) -> str:
        if signals.night_owl:
            return "keyboard"
        if resting or self.energy < NAP_BELOW:
            return "asleep"
        if now < self.sulk_until and signals.leetcode.solved_today == 0:
            return "sulking"
        if self.food < 10:
            return "starving"
        if self.food < 30:
            return "hungry"
        if now < self.party_until:
            return "party"
        if signals.leetcode.solved_today > 0:
            return "happy"
        if signals.weather.wet:
            return "rainy"
        if self.joy < 30:
            return "bored"
        return "content"

    def _hunger_note(self, signals: Signals) -> List[str]:
        day = signals.now.date().isoformat()
        if self.mood in ("hungry", "starving") and self.hungry_note_day != day and 10 <= signals.now.hour <= 21:
            self.hungry_note_day = day
            return [f"🐟 {self.name} is hungry. Solve a LeetCode problem to feed it."]
        return []

    def _growth_notes(self) -> List[str]:
        notes = []
        if self.level > self.level_seen:
            notes.append(f"⭐ {self.name} reached level {self.level}!")
            self.level_seen = self.level
        if self.stage != self.stage_seen:
            notes.append(f"✨ {self.name} grew up: now a {self.stage} cat!" if self.stage != "legend"
                         else f"👑 {self.name} became a legend.")
            self.stage_seen = self.stage
        return notes

    # ------------------------------------------------------------------ #
    # interactions
    # ------------------------------------------------------------------ #

    def pet(self, now: Optional[float] = None) -> Tuple[bool, str]:
        now = now or time.time()
        if now - self.last_pet < PET_COOLDOWN:
            return False, f"{self.name} just got petted. It purrs anyway. (again in {_wait(PET_COOLDOWN - (now - self.last_pet))})"
        self.last_pet = now
        self.joy = _clamp(self.joy + 12)
        self.xp += 2
        self.totals["pets"] = self.totals.get("pets", 0) + 1
        return True, f"{self.name} purrs and headbutts your hand. 💞"

    def treat(self, now: Optional[float] = None, today: str = "") -> Tuple[bool, str]:
        now = now or time.time()
        if self.treats_day != today:
            self.treats_day, self.treats_used = today, 0
        if self.treats_used >= TREATS_PER_DAY:
            return False, f"No more treats today ({TREATS_PER_DAY}/day). Real food = LeetCode problems. 🐟"
        if now - self.last_treat < TREAT_COOLDOWN:
            return False, f"{self.name} is still munching. Next treat in {_wait(TREAT_COOLDOWN - (now - self.last_treat))}."
        self.last_treat = now
        self.treats_used += 1
        self.food = _clamp(self.food + 15)
        self.joy = _clamp(self.joy + 5)
        self.xp += 3
        self.totals["treats"] = self.totals.get("treats", 0) + 1
        return True, f"{self.name} gobbles the treat. 😋 ({self.treats_used}/{TREATS_PER_DAY} today)"

    def visitor(self, who: str, action: str) -> str:
        """A friend in a group pets or feeds Kitty (cooldowns are kept by the plugin)."""
        self.last_visitor = who
        self.totals["visitor_pets"] = self.totals.get("visitor_pets", 0) + 1
        if action == "feed":
            self.food = _clamp(self.food + 8)
            self.joy = _clamp(self.joy + 4)
            return f"😋 {self.name} happily eats the snack from {who}."
        self.joy = _clamp(self.joy + 6)
        self.xp += 1
        return f"😽 {self.name} purrs at {who}."


def _wait(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    if seconds >= 3600:
        return f"{seconds // 3600}h {seconds % 3600 // 60}m"
    return f"{max(1, seconds // 60)}m"


def bar(value: float, width: int = 10) -> str:
    full = int(round(_clamp(value) / 100 * width))
    return "▰" * full + "▱" * (width - full)


__all__ = ["Kitty", "COATS", "MOODS", "STAGES", "bar", "level_for", "xp_for_level"]
