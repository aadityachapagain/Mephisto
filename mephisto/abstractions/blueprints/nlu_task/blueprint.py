import random
import json
import shutil
import subprocess
from dataclasses import dataclass, field
import os
from typing import Dict, Any, List

from mephisto.abstractions.blueprints.static_react_task.static_react_blueprint import (
    StaticReactBlueprint,
    StaticReactBlueprintArgs,
    StaticReactTaskBuilder
)
from mephisto.operations.registry import register_mephisto_abstraction

TASK_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
NLU_BLUEPRINT_TYPE = 'nlu_task'


@dataclass
class IntentArgs:
    name: str = field(default='', metadata={"help": "Name of intent"})
    instruction: str = field(default='', metadata={'help': "Mturk instruction for this intent"})


@dataclass
class NLUTaskBlueprintArgs(StaticReactBlueprintArgs):
    _blueprint_type: str = NLU_BLUEPRINT_TYPE
    _group: str = field(
        default="NLUTaskStaticBlueprint",
        metadata={
            'help': """This task ask for utterances and NLU annotations on them."""
        },
    )

    max_submission_per_run_qualification: str = field(default='', metadata={"help": "Qualification given to worker performing max hit"})
    clean_max_submission_per_run_qualification: str = field(default='', metadata={"help": "Clean the max submission qualifications"})
    super_worker_qualification: str = field(default='', metadata={"help": "Qualification used to whitelist super workers"})
    email_super_workers: bool = field(default=False, metadata={"help": "Whether to email superworkers or not"})
    approve_super_workers_prev_hits: bool = field(default=False, metadata={"help": "Approve super workers previous hits"})
    email_super_worker_subject: str = field(default='', metadata={"help": "Email subject sent to super worker"})
    email_super_worker_message: str = field(default='', metadata={"help": "Email message body sent to super worker"})
    task_dir: str = TASK_DIRECTORY
    min_persons: int = field(default=0, metadata={"help": "Minimum number of persons to be mentioned in the sentence, 0 for not checking"})
    subtasks_per_unit: int = field(
        default=1, metadata={"help": "Number of subtasks(NLU annotations) to do per unit"}
    )
    onboarding_subtasks_per_unit: int = field(default=1, metadata={
        "help": "Number of subtasks(NLU annotations) to do per unit during onboarding."})
    onboarding_hamming_score_threshold: float = field(default=0.6, metadata={
        "help": "Hamming score threshold to pass qualification"})
    onboarding_data_path: str = field(default='', metadata={"help": "Path to json file for onboarding data."})
    onboarding_instruction: str = field(default='', metadata={"help": "Instruction for onboarding qualification task."})
    utterances_per_intents: int = field(default=2, metadata={"help": "Number of utterances to collect per each intent"})
    intents: List[IntentArgs] = field(default_factory=list,
                                      metadata={"help": "List on intents you want to collect utterances"})
    intent_task_names: List[str] = field(default_factory=list, metadata={
        "help": "List of intent task name to use in the run, all if not specified"})
    compulsory_relations: List[str] = field(default_factory=list, metadata={"help": "Relations must be specified by workers"})
    entities: List[str] = field(default_factory=list,
                                metadata={"help": "List on entities that need to be included in utterances"})
    relation_types: Any = field(default_factory=dict,
                                metadata={"help": "List of relation types to include in sentences"})
    qual_relation_types: Any = field(default_factory=dict,
                                     metadata={"help": "List of relation types to include in qualification task"})
    random_seed: int = 42
    allowed_countries: List[str] = field(default_factory=list, metadata={"help": "List on allowed countries"})
    no_person: bool = field(default=False, metadata={"help": "Whether person is required to mention by worker."})


class NLUTaskBuilder(StaticReactTaskBuilder):
    def build_in_dir(self, build_dir: str):
        task_dir = self.args.blueprint.get("task_dir", TASK_DIRECTORY)
        frontend_source_dir = os.path.join(task_dir, "webapp")
        frontend_build_dir = os.path.join(frontend_source_dir, "build")

        return_dir = os.getcwd()
        os.chdir(frontend_source_dir)
        if os.path.exists(frontend_build_dir):
            shutil.rmtree(frontend_build_dir)
        packages_installed = subprocess.call(["npm", "install"])
        if packages_installed != 0:
            raise Exception(
                "please make sure npm is installed, otherwise view "
                "the above error for more info."
            )

        webpack_complete = subprocess.call(["npm", "run", "dev"])
        if webpack_complete != 0:
            raise Exception(
                "Webpack appears to have failed to build your "
                "frontend. See the above error for more information."
            )
        os.chdir(return_dir)
        super(NLUTaskBuilder, self).build_in_dir(build_dir)


@register_mephisto_abstraction()
class NLUTaskBlueprint(StaticReactBlueprint):
    TaskBuilderClass = NLUTaskBuilder
    ArgsClass = NLUTaskBlueprintArgs
    BLUEPRINT_TYPE = NLU_BLUEPRINT_TYPE

    def __init__(
            self, task_run: "TaskRun", args: "DictConfig", shared_state: "SharedTaskState"
    ):
        super(StaticReactBlueprint, self).__init__(task_run, args, shared_state)
        self.onboarding_data = []
        with open(self.args.blueprint.onboarding_data_path) as onboarding_data_path:
            for idx, data in enumerate(json.load(onboarding_data_path)['utterances']):
                data['idx'] = idx
                self.onboarding_data.append(data)

    def get_frontend_args(self) -> Dict[str, Any]:
        return_values = super(NLUTaskBlueprint, self).get_frontend_args()
        return_values.update({
            'min_persons': self.args.blueprint.get('min_persons', 0),
            'subtasks_per_unit': self.args.blueprint.get('subtasks_per_unit', 1),
            'entities': list(self.args.blueprint.get('entities', [])),
            'relation_types': {k: list(v) for k, v in self.args.blueprint.get('relation_types', dict()).items()},
            'qual_relation_types': {k: list(v) for k, v in self.args.blueprint.get('qual_relation_types', dict()).items()},
            'onboarding_instruction': self.args.blueprint.get('onboarding_instruction', ''),
            'compulsory_relations': list(self.args.blueprint.get('compulsory_relations', [])),
            'no_person': self.args.blueprint.get('no_person', False),
        })
        return return_values

    @classmethod
    def assert_task_args(
            cls, args: "DictConfig", shared_state: "SharedTaskState"
    ) -> None:
        super(StaticReactBlueprint, cls).assert_task_args(args, shared_state)
        found_task_source = args.blueprint.task_source
        assert (
                found_task_source is not None
        ), "Must provide a path to a javascript bundle in `task_source`"
        # found_task_path = os.path.expanduser(found_task_source)
        # assert os.path.exists(
        #     found_task_path
        # ), f"Provided task source {found_task_path} does not exist."

    def validate_onboarding(
            self, worker: "Worker", onboarding_agent: "OnboardingAgent"
    ) -> bool:
        onboarding_data = onboarding_agent.state.get_data()
        # add answers to data
        for data in onboarding_data['inputs']:
            data['persons'] = self.onboarding_data[data['idx']]['persons']
        return self.shared_state.validate_onboarding(onboarding_data)

    def get_onboarding_data(self, worker_id: str) -> List[Dict[str, Any]]:
        onboarding_data = random.sample(super().get_onboarding_data(worker_id),
                                        self.args.blueprint.onboarding_subtasks_per_unit)
        # remove answers from data
        return [{k: v for k, v in data.items() if k != 'persons'} for data in onboarding_data]
