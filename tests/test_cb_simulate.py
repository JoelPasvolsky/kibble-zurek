# Copyright 2024 D-Wave
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import pytest

from contextvars import copy_context
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

import datetime

from app import SimulateReturn, run_button_click, simulate

before_test = datetime.datetime.now().strftime('%c')
parametrize_vals = [
    (512, "512, 1024", 'SUBMITTED', no_update),
    (2048, "512, 1024", 'EMBEDDING', 'needed')
]

@pytest.mark.parametrize(
    'spins_val, cached_embedding_lengths_val, submit_state_out, embedding_found', 
    parametrize_vals)
def test_simulate_button_press(spins_val, cached_embedding_lengths_val, submit_state_out, 
                               embedding_found):
    """Test pressing Simulate button initiates submission."""

    def run_callback():
        context_value.set(AttributeDict(
            **{"triggered_inputs": [{"prop_id": "btn_simulate.n_clicks"}]}))

        return run_button_click(1, 'READY', cached_embedding_lengths_val, spins_val,
            'Advantage_system4.3')
    
    ctx = copy_context()

    output = ctx.run(run_callback)

    assert output[0:4] == (True, False, 0, submit_state_out)
    assert output[5] == embedding_found

def mock_get_status(client, job_id, job_submit_time):

    if job_id == 'first few attempts':
        return None
    if job_id == 'first returned status':
        return 'PENDING'
    if job_id == 'early returning statuses':
        return 'PENDING'
    if job_id == '-1':
        return 'ERROR'
    if job_id == '0':
        return 'EMBEDDING'
    if job_id == '1':
        return 'IN_PROGRESS'
    if job_id == '2':
        return 'COMPLETED'
    if job_id == '3':
        return 'CANCELLED'
    if job_id == '4':
        return 'FAILED'

class mock_qpu_edges():
    def __init__(self, edges):
        self.edges = edges

class mock_qpu(object):
    def __init__(self):
        self.edges_per_qpu = {'Advantage_system4.3': "dummy"}
    def __getitem__(self, indx):
        return mock_qpu_edges(self.edges_per_qpu[indx])

def mock_find_embedding(spins, dummy_edges):
    if spins == 'yes':
        return {1: [10], 2: [20]}
    if spins == 'no':
        return {}

parametrize_names = 'job_id_val, job_submit_state_in, ' +  \
    'spins_val, embeddings_found_in, btn_simulate_disabled_out, wd_job_disabled_out, ' + \
    'wd_job_intervals_out, wd_job_n_out, job_submit_state_out, job_submit_time_out, ' + \
    'embedding_found_out'

parametrize_vals = [
    (-1, 'READY', 512, 'dummy embeddings found', False, True,
     no_update, no_update, 'ERROR', no_update, no_update),
    ('first few attempts', 'SUBMITTED', 512, 'dummy embeddings found', no_update, no_update,
    200, 0, 'SUBMITTED', no_update, no_update),
    ('first returned status', 'SUBMITTED', 512, 'dummy embeddings found', no_update, no_update,
    1000, 0, 'PENDING', no_update, no_update),
    ('1', 'PENDING', 512, 'dummy embeddings found', no_update, no_update,
    1000, 0, 'IN_PROGRESS', no_update, no_update),
    ('1', 'IN_PROGRESS', 512, 'dummy embeddings found', no_update, no_update,
    1000, 0, 'IN_PROGRESS', no_update, no_update),
    ('2', 'IN_PROGRESS', 512, 'dummy embeddings found', no_update, no_update,
    1000, 0, 'COMPLETED', no_update, no_update),
    ('2', 'COMPLETED', 512, 'dummy embeddings found', False, True,
    no_update, no_update, no_update, no_update, no_update),
    ('3', 'CANCELLED', 512, 'dummy embeddings found', False, True,
    no_update, no_update, no_update, no_update, no_update),
    ('4', 'FAILED', 512, 'dummy embeddings found', False, True,
    no_update, no_update, no_update, no_update, no_update),
    ('dummy', 'EMBEDDING', 'yes', 'needed', no_update, no_update,
    200, 0, 'EMBEDDING', no_update, {'yes': {1: [10], 2: [20]}}),
    ('dummy', 'EMBEDDING', 'no', 'needed', False, True,
    no_update, no_update, 'FAILED', no_update, 'not found'),
    ('dummy', 'EMBEDDING', 'no', 'not needed', no_update, no_update,
    200, no_update, 'SUBMITTED', before_test, no_update)
]

@pytest.mark.parametrize(parametrize_names, parametrize_vals)
def test_simulate_states(mocker, job_id_val, job_submit_state_in,
                         spins_val, embeddings_found_in, btn_simulate_disabled_out, 
                         wd_job_disabled_out, wd_job_intervals_out, wd_job_n_out, 
                         job_submit_state_out, job_submit_time_out, embedding_found_out):
    """Test transitions between states."""

    mocker.patch('app.get_job_status', new=mock_get_status)
    mocker.patch('app.qpus', new=mock_qpu())
    mocker.patch('app.find_one_to_one_embedding', new=mock_find_embedding)

    def run_callback():
        context_value.set(AttributeDict(
            **{"triggered_inputs": [{"prop_id": "wd_job.n_intervals"}]}))

        return simulate(1, job_id_val, job_submit_state_in, before_test,
                        spins_val, 'Advantage_system4.3', embeddings_found_in)

    ctx = copy_context()

    output = ctx.run(run_callback)

    expected_output = SimulateReturn(
        btn_simulate_disabled=btn_simulate_disabled_out,
        wd_job_disabled=wd_job_disabled_out,
        wd_job_interval=wd_job_intervals_out,
        wd_job_n_intervals=wd_job_n_out,
        job_submit_state=job_submit_state_out,
        job_submit_time=job_submit_time_out,
        embeddings_found=embedding_found_out,
    )

    assert output[0:5] == expected_output[0:5]
    assert output[6] == expected_output[6]
    # One could test ``job_submit_time_out >= before_test`` to little gain, much complication