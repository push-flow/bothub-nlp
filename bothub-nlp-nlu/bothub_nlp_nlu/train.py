import requests
from tempfile import mkdtemp
from collections import defaultdict

from rasa_nlu.model import Trainer
from rasa_nlu.training_data import Message, TrainingData
from rasa_nlu.components import ComponentBuilder
from rasa_nlu.training_data.formats.readerwriter import TrainingDataWriter
from rasa_nlu.utils import json_to_string
from django.db import models

from .utils import get_rasa_nlu_config_from_update
from .utils import PokeLogging
from .persistor import BothubPersistor
from . import logger


class BothubWriter(TrainingDataWriter):
    def dumps(self, training_data, **kwargs):
        js_entity_synonyms = defaultdict(list)
        for k, v in training_data.entity_synonyms.items():
            if k != v:
                js_entity_synonyms[v].append(k)

        formatted_synonyms = [{'value': value, 'synonyms': syns}
                              for value, syns in js_entity_synonyms.items()]

        formatted_examples = [
            example.as_dict()
            for example in training_data.training_examples
        ]
        formatted_label_examples = [
            example.as_dict()
            for example in training_data.label_training_examples or []
        ]

        return json_to_string({
            'rasa_nlu_data': {
                'common_examples': formatted_examples,
                'label_examples': formatted_label_examples,
                'regex_features': training_data.regex_features,
                'entity_synonyms': formatted_synonyms,
            }
        }, **kwargs)


class BothubTrainingData(TrainingData):
    def __init__(self, label_training_examples=None, **kwargs):
        if label_training_examples:
            self.label_training_examples = self.sanitize_examples(
                label_training_examples)
        else:
            self.label_training_examples = []
        super().__init__(**kwargs)

    def as_json(self, **kwargs):
        return BothubWriter().dumps(self)


def request_backend_start_training(update_id, by):
    backend = 'http://33d0c44b.ngrok.io'
    update = requests.post(
        '{}/v2/repository/nlp/authorization/train/starttraining/'.format(
            backend
        ),
        data={
            "update_id": update_id,
            "by_user": by
        }
    ).json()
    return update


def request_backend_get_entities(update_id, language, example_id):
    backend = 'http://33d0c44b.ngrok.io'
    update = requests.get(
        '{}/v2/repository/nlp/authorization/train/getentities/?update_id={}&language={}&example_id={}'.format(
            backend,
            update_id,
            language,
            example_id
        )
    ).json()
    return update

def request_backend_get_entities_label(update_id, language, example_id):
    backend = 'http://33d0c44b.ngrok.io'
    update = requests.get(
        '{}/v2/repository/nlp/authorization/train/getentitieslabel/?update_id={}&language={}&example_id={}'.format(
            backend,
            update_id,
            language,
            example_id
        )
    ).json()
    return update


def request_backend_get_text(update_id, language, example_id):
    backend = 'http://33d0c44b.ngrok.io'
    update = requests.get(
        '{}/v2/repository/nlp/authorization/train/gettext/?update_id={}&language={}&example_id={}'.format(
            backend,
            update_id,
            language,
            example_id
        )
    ).json()
    return update

def request_backend_trainfail(update_id):
    backend = 'http://33d0c44b.ngrok.io'
    update = requests.post(
        '{}/v2/repository/nlp/authorization/train/trainfail/'.format(
            backend
        ),
        data={
            'update_id': update_id
        }
    ).json()
    return update

def request_backend_traininglog(update_id, training_log):
    backend = 'http://33d0c44b.ngrok.io'
    update = requests.post(
        '{}/v2/repository/nlp/authorization/train/traininglog/'.format(
            backend
        ),
        data={
            'update_id': update_id,
            'training_log': training_log
        }
    ).json()
    return update


def train_update(update, by):
    update_request = request_backend_start_training(update, by)
    with PokeLogging() as pl:
        try:
            # examples = [
            #     Message.build(
            #         text=example.get_text(update_request.get('language')),
            #         intent=example.intent,
            #         entities=[
            #             example_entity.rasa_nlu_data
            #             for example_entity in example.get_entities(
            #                 update_request.get('language'))])
            #     for example in update_request.get('examples')]

            examples = []

            for example in update_request.get('examples'):
                entities = []
                request_entities = request_backend_get_entities(
                    update, 
                    update_request.get('language'),
                    example.get('example_id')
                )
                for example_entity in request_entities.get('entities'):
                    entities.append(example_entity)

                examples.append(
                    Message.build(
                        # text=example.get_text(update_request.get('language')),
                        text=request_backend_get_text(
                            update, 
                            update_request.get('language'), 
                            example.get('example_id')
                        ).get('get_text'),
                        intent=example.get('example_intent'),
                        entities=entities
                    )
                )
            

            label_examples_query = update_request.get('label_examples_query')

            # label_examples = [
            #     Message.build(
            #         text=example.get_text(update_request.get('language')),
            #         entities=[
            #             example_entity.get_rasa_nlu_data(
            #                 label_as_entity=True)
            #             for example_entity in filter(
            #                 lambda ee: ee.entity.label,
            #                 example.get_entities(update_request.get('language')))
            #         ]
            #     )
            #     for example in label_examples_query]###


            label_examples = []

            for example in label_examples_query:
                entities = []
                request_entities = request_backend_get_entities_label(
                    update, 
                    update_request.get('language'),
                    example.get('example_id')
                )
                for example_entity in request_entities.get('entities'):
                    entities.append(example_entity)

                label_examples.append(
                    Message.build(
                        # text=example.get_text(update_request.get('language')),
                        text=request_backend_get_text(
                            update, 
                            update_request.get('language'), 
                            example.get('example_id')
                        ).get('get_text'),
                        entities=entities
                    )
                )
            

            rasa_nlu_config = get_rasa_nlu_config_from_update(update_request)
            trainer = Trainer(
                rasa_nlu_config,
                ComponentBuilder(use_cache=False))
            training_data = BothubTrainingData(
                label_training_examples=label_examples,
                training_examples=examples)

            trainer.train(training_data)

            persistor = BothubPersistor(update)
            trainer.persist(
                mkdtemp(),
                persistor=persistor,
                project_name=str(update_request.get('repository_uuid')),
                fixed_model_name=str(update_request.get('update_id')))
        except Exception as e:
            logger.exception(e)
            # update.train_fail()
            request_backend_trainfail(update)
            raise e
        finally:
            request_backend_traininglog(update, pl.getvalue())
            # update.training_log = pl.getvalue()
            # update.save(update_fields=['training_log'])
