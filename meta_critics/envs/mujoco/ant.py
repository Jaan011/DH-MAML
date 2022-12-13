"""
this ported env for mujoco 1.2 /  1.3 it uses
direct python - C binding.  i.e don't use mujoco-py


Ant environment with target position.

The ant follows the dynamics from MuJoCo [1], and receives at each
time step a reward composed of a control cost, a contact cost, a survival
reward, and a penalty equal to its L1 distance to the target position. The
tasks are generated by sampling the target positions from the uniform
distribution on [-3, 3]^2.

[1] Emanuel Todorov, Tom Erez, Yuval Tassa, "MuJoCo: A physics engine for
   model-based control", 2012
   (https://homes.cs.washington.edu/~todorov/papers/TodorovIROS12.pdf)


Bunch of fixed added to fix all mujoco
Mus
"""
import numpy as np
from gym.envs.mujoco.ant_v4 import AntEnv as AntEnv_
from gym.envs.mujoco import MujocoEnv


class AntEnv(AntEnv_, MujocoEnv):
    metadata = {
        "render_modes": [
            "human",
            "rgb_array",
            "depth_array",
        ],
        "render_fps": 20,
    }

    @property
    def action_scaling(self):
        """
        :return:
        """
        if (not hasattr(self, 'action_space')) or (self.action_space is None):
            return 1.0

        if self._action_scaling is None:
            lb, ub = self.action_space.low, self.action_space.high
            self._action_scaling = 0.5 * (ub - lb)

        return self._action_scaling

    def _get_obs(self):
        """
        :return:
        """

        return np.concatenate([
            self.data.qpos.flat.copy(),
            self.data.qvel.flat.copy(),
            np.clip(self.data.cfrc_ext, -1, 1).flat,
            self.data.get_body_xmat("torso").flat,
            self.get_body_com("torso").flat,
        ]).astype(np.float32).flatten()

    def viewer_setup(self):
        """

        :return:
        """
        camera_id = self.model.camera_name2id('track')
        self.viewer.cam.type = 2
        self.viewer.cam.fixedcamid = camera_id
        self.viewer.cam.distance = self.model.stat.extent * 0.35
        # Hide the overlay
        self.viewer._hide_overlay = True

    def render(self, mode='human'):
        """
        :param mode:
        :return:
        """
        if mode == 'rgb_array':
            self._get_viewer(mode).render()
            # window size used for old mujoco-py:
            width, height = 500, 500
            data = self._get_viewer(mode).read_pixels(width, height, depth=False)
            return data
        elif mode == 'human':
            self._get_viewer(mode).render()


class AntVelEnv(AntEnv, MujocoEnv):
    """Ant environment with target velocity, as described in [1]. The 
    code is adapted from
    https://github.com/cbfinn/maml_rl/blob/9c8e2ebd741cb0c7b8bf2d040c4caeeb8e06cc95/rllab/envs/mujoco/ant_env_rand.py

    The ant follows the dynamics from MuJoCo [2], and receives at each 
    time step a reward composed of a control cost, a contact cost, a survival 
    reward, and a penalty equal to the difference between its current velocity 
    and the target velocity. The tasks are generated by sampling the target 
    velocities from the uniform distribution on [0, 3].

    [1] Chelsea Finn, Pieter Abbeel, Sergey Levine, "Model-Agnostic 
        Meta-Learning for Fast Adaptation of Deep Networks", 2017 
        (https://arxiv.org/abs/1703.03400)
    [2] Emanuel Todorov, Tom Erez, Yuval Tassa, "MuJoCo: A physics engine for 
        model-based control", 2012 
        (https://homes.cs.washington.edu/~todorov/papers/TodorovIROS12.pdf)
    """

    def __init__(self, task=None, low=0.0, high=3.0, **kwargs):
        if task is None:
            task = {}
        super(AntVelEnv, self).__init__(self,
                                        xml_file="ant.xml",
                                        ctrl_cost_weight=0.5,
                                        use_contact_forces=False,
                                        contact_cost_weight=5e-4,
                                        healthy_reward=1.0,
                                        terminate_when_unhealthy=True,
                                        healthy_z_range=(0.2, 1.0),
                                        contact_force_range=(-1.0, 1.0),
                                        reset_noise_scale=0.1,
                                        exclude_current_positions_from_observation=True,
                                        **kwargs)
        self._task = task
        self.low = low
        self.high = high
        self._goal_vel = task.get('velocity', 0.0)
        self._action_scaling = None

    def step(self, action):
        xposbefore = self.get_body_com("torso")[0]
        self.do_simulation(action, self.frame_skip)
        xposafter = self.get_body_com("torso")[0]

        forward_vel = (xposafter - xposbefore) / self.dt
        forward_reward = -1.0 * np.abs(forward_vel - self._goal_vel) + 1.0
        survive_reward = 0.05

        ctrl_cost = 0.5 * 1e-2 * np.sum(np.square(action / self.action_scaling))
        contact_cost = 0.5 * 1e-3 * np.sum(
                np.square(np.clip(self.data.cfrc_ext, -1, 1)))

        observation = self._get_obs()
        reward = forward_reward - ctrl_cost - contact_cost + survive_reward
        state = self.state_vector()
        notdone = np.isfinite(state).all() \
                  and 0.2 <= state[2] <= 1.0

        done = not notdone
        infos = dict(reward_forward=forward_reward,
                     reward_ctrl=-ctrl_cost,
                     reward_contact=-contact_cost,
                     reward_survive=survive_reward,
                     task=self._task)
        return observation, reward, done, False, infos

    def sample_tasks(self, num_tasks):
        velocities = self.np_random.uniform(self.low, self.high, size=(num_tasks,))
        tasks = [{'velocity': velocity} for velocity in velocities]
        return tasks

    def reset_task(self, task):
        self._task = task
        self._goal_vel = task['velocity']


class AntDirEnv(AntEnv, MujocoEnv):
    """Ant environment with target direction, as described in [1]. The 
    code is adapted from
    https://github.com/cbfinn/maml_rl/blob/9c8e2ebd741cb0c7b8bf2d040c4caeeb8e06cc95/rllab/envs/mujoco/ant_env_rand_direc.py

    The ant follows the dynamics from MuJoCo [2], and receives at each 
    time step a reward composed of a control cost, a contact cost, a survival 
    reward, and a reward equal to its velocity in the target direction. The 
    tasks are generated by sampling the target directions from a Bernoulli 
    distribution on {-1, 1} with parameter 0.5 (-1: backward, +1: forward).

    [1] Chelsea Finn, Pieter Abbeel, Sergey Levine, "Model-Agnostic 
        Meta-Learning for Fast Adaptation of Deep Networks", 2017 
        (https://arxiv.org/abs/1703.03400)
    [2] Emanuel Todorov, Tom Erez, Yuval Tassa, "MuJoCo: A physics engine for 
        model-based control", 2012 
        (https://homes.cs.washington.edu/~todorov/papers/TodorovIROS12.pdf)
    """

    def __init__(self, task=None):
        if task is None:
            task = {}
        self._task = task
        self._goal_dir = task.get('direction', 1)
        self._action_scaling = None
        super(AntDirEnv, self).__init__()

    def step(self, action):
        xposbefore = self.get_body_com("torso")[0]
        self.do_simulation(action, self.frame_skip)
        xposafter = self.get_body_com("torso")[0]

        forward_vel = (xposafter - xposbefore) / self.dt
        forward_reward = self._goal_dir * forward_vel
        survive_reward = 0.05

        ctrl_cost = 0.5 * 1e-2 * np.sum(np.square(action / self.action_scaling))
        contact_cost = 0.5 * 1e-3 * np.sum(
                np.square(np.clip(self.data.cfrc_ext, -1, 1)))

        observation = self._get_obs()
        reward = forward_reward - ctrl_cost - contact_cost + survive_reward
        state = self.state_vector()
        notdone = np.isfinite(state).all() and 0.2 <= state[2] <= 1.0
        done = not notdone
        infos = dict(reward_forward=forward_reward,
                     reward_ctrl=-ctrl_cost,
                     reward_contact=-contact_cost,
                     reward_survive=survive_reward,
                     task=self._task)
        return observation, reward, done, infos

    def sample_tasks(self, num_tasks):
        directions = 2 * self.np_random.binomial(1, p=0.5, size=(num_tasks,)) - 1
        tasks = [{'direction': direction} for direction in directions]
        return tasks

    def reset_task(self, task):
        self._task = task
        self._goal_dir = task['direction']


class AntPosEnv(AntEnv, MujocoEnv):

    def __init__(self, task=None, low=-3.0, high=3.0):
        if task is None:
            task = {}
        self._task = task
        self.low = low
        self.high = high

        self._goal_pos = task.get('position', np.zeros((2,), dtype=np.float32))
        self._action_scaling = None
        super(AntPosEnv, self).__init__()

    def step(self, action):
        self.do_simulation(action, self.frame_skip)
        xyposafter = self.get_body_com("torso")[:2]

        goal_reward = -np.sum(np.abs(xyposafter - self._goal_pos)) + 4.0
        survive_reward = 0.05

        ctrl_cost = 0.5 * 1e-2 * np.sum(np.square(action / self.action_scaling))
        contact_cost = 0.5 * 1e-3 * np.sum(
                np.square(np.clip(self.data.cfrc_ext, -1, 1)))

        observation = self._get_obs()
        reward = goal_reward - ctrl_cost - contact_cost + survive_reward
        state = self.state_vector()
        notdone = np.isfinite(state).all() and 0.2 <= state[2] <= 1.0
        done = not notdone
        infos = dict(reward_goal=goal_reward,
                     reward_ctrl=-ctrl_cost,
                     reward_contact=-contact_cost,
                     reward_survive=survive_reward,
                     task=self._task)
        return observation, reward, done, infos

    def sample_tasks(self, num_tasks):
        positions = self.np_random.uniform(self.low, self.high, size=(num_tasks, 2))
        tasks = [{'position': position} for position in positions]
        return tasks

    def reset_task(self, task):
        self._task = task
        self._goal_pos = task['position']
