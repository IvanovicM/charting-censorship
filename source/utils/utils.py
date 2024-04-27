import json
import logging
import os
import pycountry

from datetime import date

LOG_DIR = 'logs'
TODAY = date.today().strftime('%Y%m%d')

# In alphabetical order, based on their full time
COUNTRIES = ['AU', 'BR', 'CN', 'FR', 'DE', 'IN', 'IR', 'IT', 'NL', 'RU', 'SG', 'ZA', 'CH', 'UA', 'GB', 'US']

HEG_GROUPS = {
    'United-States': ['US'],
    'Five-Eyes': ['US', 'GB', 'AU', 'CA', 'NZ'],
    'European-Union': ['BE', 'BG', 'CZ', 'DK', 'DE', 'EE', 'IE', 'EL', 'ES', 'FR', 'HR', 'IT', 'CY', 'LV', 'LT', 'LU', 'HU', 'MT', 'NL', 'AT', 'PL', 'PT', 'RO', 'SI', 'SK', 'FI', 'SE', 'EU'],
    'Iran-China-Russia': ['IR', 'RU', 'CN']
}

def check_make_save_file_dir(file_path):
    dirname = os.path.dirname(file_path)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)

def enable_logger(log_sub_file_name, log_dir=LOG_DIR):
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir) 
    
    logger = logging.getLogger()
    log_file = f'{log_dir}/{log_sub_file_name}.{TODAY}.logs.txt'
    fhandler = logging.FileHandler(filename=log_file, mode='a')
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
    )
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)
    logger.setLevel(logging.INFO)

def log_elapsed_time(elapsed):
    hours, rem = divmod(elapsed, 3600)
    minutes, seconds = divmod(rem, 60)
    s = '{:0>2}:{:0>2}:{:05.2f}'.format(int(hours), int(minutes), seconds)
    logging.info(f'Time elapsed: {s}\n')

def rst_log_counter(counter_max_value):
    global lcounter, lcounter_max
    lcounter = 0
    lcounter_max = counter_max_value

def log_counter(modulo=1000, info=None):
    global lcounter
    if lcounter % modulo == 0:
        str_info = ''
        if info is not None:
            str_info = f' ({info})'
        logging.info(f'Processing: {lcounter + 1} / {lcounter_max}{str_info}')
    lcounter += 1

def sort_dict(d, reverse=True):
    return {
        k: v
        for k, v in sorted(d.items(), key=lambda item: item[1], reverse=reverse)
    }

def pretty_print(json_dict, sort_keys=False):
    print(json.dumps(json_dict, indent=4, sort_keys=sort_keys))

def print_divider(ch='~'):
    print(150*ch)

def country_name(a2_country_code):
    country_map = {
        'CH': 'Switzerland',
        'CN': 'China',
        'GB': 'U.K.',
        'IN': 'India',
        'IR': 'Iran',
        'RU': 'Russia',
        'US': 'United States',
        'BR': 'Brazil',
        'DE': 'Germany',
        'FR': 'France',
        'IT': 'Italy',
        'NL': 'Netherlands',
        'SG': 'Singapore',
        'AU': 'Australia',
        'UA': 'Ukraine',
        'ZA': 'South Africa',
        'EU': 'European Union',
        '': ''
    }
    if a2_country_code in country_map.keys():
        return country_map[a2_country_code]
    return pycountry.countries.get(alpha_2=a2_country_code).name
