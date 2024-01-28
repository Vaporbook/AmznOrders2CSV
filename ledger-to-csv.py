import json
import re
import pandas as pd


LEDGER_FILENAME = 'ledger.json'

def parse_order(id, raw):
    #print(raw)
    working_str = re.sub('Order Summary', '', raw, flags=re.IGNORECASE)
    working_str = re.sub('See tax and seller information', '', working_str, flags=re.IGNORECASE)
    # fix the missing semicolon on the refund line
    working_str = re.sub("Refund Total\n", "Refund Total:\n", working_str, flags=re.IGNORECASE)
    # remove newlines appearing after :
    working_str = re.sub(':\n', ': ', working_str).strip()

    order_object = {}
    order_object['id'] = id
    col_values = working_str.split('\n')
    for col_value in col_values:
        #print(f'col_value:{col_value}')
        try:
            label, value = col_value.split(':')
            label = label.strip()
            value = value.strip()
            order_object[label] = value
        except Exception as error:
            pass
    return order_object

print('reading ledger file...')

ledger_file = open(LEDGER_FILENAME, 'r')
order_data = json.load(ledger_file)
order_objects = []
for order in order_data:
    id = order[0]
    raw = order[1]
    order_objects.append(parse_order(id, raw))

df = pd.DataFrame(data=order_objects)

#print(df)
print('writing...')
df.to_csv('ledger.csv')
print('done.')

