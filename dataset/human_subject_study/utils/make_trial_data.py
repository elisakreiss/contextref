import csv, json
from collections import defaultdict

clean_data_file = 'data/clean_data.csv'

def make_recursive_dict() :
    return defaultdict(make_recursive_dict)

def load_variables(observation) :
    """
    load in relevant variables from an observation
    """
    topic, context = observation['topic'], observation['context']
    img_id, filename = observation['img_id'], observation['image']
    description = observation['final_description']

    return topic, context, img_id, filename, description
        
def dict_of_dicts_into_list(dictionary, keyname) :
    """
    takes a dictionary with (key, value) as type(key) == str and type(value) == dict
    and converts it into a list with elements being dictionaries that are the same as
    value but with a new keyname:key mapping added
    """
    for key, value in dictionary.items() :
        value[keyname] = key
    
    return list(dictionary.values())

trial_data = make_recursive_dict()

with open(clean_data_file, 'r') as f :
    observations = list(csv.DictReader(f))
    for observation in observations :
        topic, context, img_id, filename, description = load_variables(observation)
        image = trial_data[filename]
        image['img_id'] = img_id
        image['topic'] = topic
        if 'descriptions' not in image :
            image['descriptions'] = defaultdict(list)
        image['descriptions'][context].append(description)

trial_data = dict_of_dicts_into_list(trial_data, 'filename')

with open('test.json', 'w') as output :
    json.dump(trial_data, output, indent='\t')

