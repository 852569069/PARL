#   Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import paddle
import paddle.nn as nn
import collections
import numpy as np

from parl.core.model_base import ModelBase
from parl.utils import machine_info

__all__ = ['Model']


class Model(nn.Layer, ModelBase):
    """
    | `alias`: ``parl.Model``
    | `alias`: ``parl.core.paddle.agent.Model``

    | ``Model`` is a base class of PARL for the neural network. 
    A ``Model`` is usually a policy or Q-value function, which predicts 
    an action or an estimate according to the environmental observation.

    | To use the ``PaddlePaddle2.0`` backend model, user needs to call 
    ``super(Model, self).__init__()`` at the beginning of ``__init__`` 
    function.

    | ``Model`` supports duplicating a ``Model`` instance in a pythonic way:

    | ``copied_model = copy.deepcopy(model)``

    Example:

    .. code-block:: python

        import parl
        import paddle.nn as nn

        class Policy(parl.Model):
            def __init__(self):
                super(Policy, self).__init__()
                self.fc = nn.Linear(input_dim=100, output_dim=32)

            def policy(self, obs):
                out = self.fc(obs)
                return out
               
        policy = Policy() 
        copied_policy = copy.deepcopy(model)

    Attributes:
        model_id(str): each model instance has its unique model_id.

    Public Functions:
        - ``sync_weights_to``: synchronize parameters of the current model 
        to another model.
        - ``get_weights``: return a list containing all the parameters of 
        the current model.
        - ``set_weights``: copy parameters from ``set_weights()`` to the model.
        - ``forward``: define the computations of a neural network. **Should** 
        be overridden by all subclasses.
        - ``parameters``: return a list containting names of parameters of 
        the model. 
    """

    def __init___(self):
        super(Model, self).__init__()

    def sync_weights_to(self, target_model, decay=0.0):
        """Synchronize parameters of current model to another model.

        target_model_weights = decay * target_model_weights 
                                    + (1 - decay) * current_model_weights

        Args:
            target_model (`parl.Model`): an instance of ``Model`` that has 
                the same neural network architecture as the current model.
            decay (float):  the rate of decline in copying parameters. 
                0 if no parameters decay when synchronizing the parameters.
            TODO: share_vars_parallel_executor (fluid.ParallelExecutor): 
                Optional. If not None, will use ``fluid.ParallelExecutor``
                to run program instead of ``fluid.Executor``.

        Example:

        .. code-block:: python

            import copy
            # create a model that has the same neural network structures.
            target_model = copy.deepcopy(model)

            # after initilizing the parameters ...
            model.sync_weights_to(target_mdodel)

        Note:
            Before calling ``sync_weights_to``, parameters of the model must 
            have been initialized.
        """
        assert not target_model is self, "cannot copy between identical model"
        assert isinstance(target_model, Model)
        assert self.__class__.__name__ == target_model.__class__.__name__, \
            "must be the same class for params syncing!"
        assert (decay >= 0 and decay <= 1)

        target_vars = dict(target_model.named_parameters())
        # target_vars = target_model.named_parameters()
        for name, var in self.named_parameters():
            target_data = decay * target_vars[name] + (1 - decay) * var
            target_vars[name] = target_data
        target_model.set_state_dict(target_vars)
        
    # def parameters(self):
    #     """Get names of all parameters in this ``Model``.

    #     Only parameters created by ``parl.layers`` are included.
    #     The order of parameter names is consistent among
    #     different instances of the same `Model`.

    #     Returns:
    #         param_names(list): list of string containing parameter names of all parameters

    #     Example:

    #     .. code-block:: python

    #         model = Model()
    #         model.parameters()

    #         # output: 
    #         ['fc0.weight', 'fc0.bias']
            
    #     """
    #     try:
    #         return self._parameter_names
    #     except AttributeError:
    #         self._parameter_names = []
    #         for name, _ in self.named_parameters():
    #             self._parameter_names.append(name)
    #         return self._parameter_names

    def get_weights(self):
        """Returns a Python list containing parameters of current model.

        Returns: a Python list containing the parameters of current model.
        """
        weights = self.state_dict()
        for key in weights.keys():
            weights[key] = np.asarray(weights[key].numpy())
        return weights

    def set_weights(self, weights):
        """Copy parameters from ``set_weights()`` to the model.
        
        Args:
            weights (list): a Python list containing the parameters.
        """
        old_weights = self.state_dict() # TODO speed up
        # assert len(old_weights) == len(weights), '{} params are expected, but got {}'.format(len(old_weights), len(weights))
        new_weights = collections.OrderedDict()
        for key in old_weights.keys():
            assert key in weights, 'weight missing key: {}'.format(key)
            assert old_weights[key].shape == list(weights[key].shape), 'key \'{}\' expect shape {}, but got {}'.format(key, old_weights[key].shape,  list(weights[key].shape))
            new_weights[key] = paddle.to_tensor(weights[key])
        self.set_state_dict(new_weights)