"""Multi-armed bandit problems with Bernoulli observations, as described
   in [1].

   At each time step, the agent pulls one of the `k` possible arms (actions),
   say `i`, and receives a reward sampled from a Bernoulli distribution with
   parameter `p_i`. The multi-armed bandit tasks are generated by sampling
   the parameters `p_i` from the uniform distribution on [0, 1].

   [1] Yan Duan, John Schulman, Xi Chen, Peter L. Bartlett, Ilya Sutskever,
       Pieter Abbeel, "RL2: Fast Reinforcement Learning via Slow Reinforcement
       Learning", 2016 (https://arxiv.org/abs/1611.02779)
   """
from __future__ import annotations

from abc import ABC
from typing import Optional, Union, List, Tuple

import gym
import numpy as np
import torch
from gym import spaces
from gym.core import ObsType

from meta_critics.envs.env_types import EnvType


class BanditEnv(gym.Env, ABC):
    def __init__(self, k: int,
                 max_reward: Optional[int] = 1,
                 out: Optional[EnvType] = EnvType.NdArray):
        super(BanditEnv, self).__init__()
        self.k = k
        self._max_reward = max_reward
        self.action_space = spaces.Discrete(self.k)
        self.observation_space = spaces.Box(low=0, high=0, shape=(1,), dtype=np.float32)
        self.out = out

    def max_reward(self) -> int:
        """Max rewards per arm for example Bernoulli it 1.0
        :return:
        """
        return self._max_reward

    def get_num_arms(self):
        """Return number of arms
        :return:
        """
        return self.k

    def sample(self) -> np.ndarray | torch.Tensor:
        """ Sampling from action space.
        :returns: Random action from action space return either ndarray or tensor
        """
        if self.out == EnvType.Tensor:
            return torch.from_numpy(self.action_space.sample())
        return self.action_space.sample()

    def obs_shape(self):
        """Return shape of observation
        :return:
        """
        if isinstance(self.observation_space, gym.spaces.Discrete):
            obs_shape = (1,)
        elif isinstance(self.observation_space, gym.spaces.Box):
            obs_shape = self.observation_space.shape
        else:
            raise ValueError("Unsupported observation space")
        return obs_shape

    def action_shape(self):
        """Return shape of action.
        :return:
        """
        if isinstance(self.action_space, gym.spaces.Box):
            action_shape = self.action_space.shape
        elif isinstance(self.action_space, gym.spaces.Discrete):
            action_shape = (1,)
        else:
            raise ValueError("Unsupported action space")
        return action_shape

    def reset(self, *, seed: Optional[Union[int, List[int]]] = None,
              options: Optional[dict] = None) -> Tuple[ObsType, dict]:
        """
        Default reset implementation.
        :param seed:
        :param options:
        :return:
        """
        super().reset(seed=seed)
        if self.render_mode == "human":
            self.render()
        return self.observation_space.sample(), {}
