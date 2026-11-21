"""Iteration identity only, for the pinned two-step serial continuation protocol.
Not a solver configuration, launch authorization, or a Python security boundary.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path


def _integer(value, name):
    if type(value) is not int:
        raise ValueError(name + ' must be an integer, not bool')
    return value


def _finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(name + ' must be a finite number, not bool')
    return value


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate contract key: ' + key)
        result[key] = value
    return result


@dataclass(frozen=True, slots=True)
class WindowContract:
    schema_version: int
    start: int
    end: int
    restart_index: int
    delta_t: float
    delta_t0: float
    cumulative_continuity: float

    def __post_init__(self):
        if _integer(self.schema_version, 'schema_version') != 1:
            raise ValueError('unsupported schema version')
        for name in ('start', 'end', 'restart_index'):
            _integer(getattr(self, name), name)
        if not 0 <= self.start <= 2147483645 or self.end != self.start + 2:
            raise ValueError('only two unit integer steps within label32 range supported')
        if not 0 <= self.restart_index <= 2147483645:
            raise ValueError('restart index outside supported range')
        if _finite(self.delta_t, 'delta_t') != 1 or _finite(self.delta_t0, 'delta_t0') != 1:
            raise ValueError('only deltaT=deltaT0=1 supported')
        _finite(self.cumulative_continuity, 'cumulative_continuity')

    @classmethod
    def from_dict(cls, data):
        keys = {'schema_version', 'start', 'end', 'restart_index', 'delta_t', 'delta_t0', 'cumulative_continuity'}
        if type(data) is not dict or set(data) != keys:
            raise ValueError('contract requires exactly the version1 keys')
        return cls(**data)

    @classmethod
    def from_json(cls, path):
        return cls.from_dict(json.loads(Path(path).read_text(), object_pairs_hook=_unique_object))

    @property
    def observed_states(self):
        return (self.start, self.start + 1, self.end)

    @property
    def output_states(self):
        return (self.start + 1, self.end)

    def index_for(self, state):
        _integer(state, 'state')
        if state not in self.observed_states:
            raise ValueError('state outside window')
        return self.restart_index + state - self.start

    def time_name(self, state):
        self.index_for(state)
        return str(state)

    @property
    def restart_time_dict(self):
        return {'value': float(self.start), 'name': str(self.start), 'index': self.restart_index,
                'deltaT': float(self.delta_t), 'deltaT0': float(self.delta_t0)}
