import pandas as pd

data = pd.read_csv('data.csv')
species = pd.read_csv('USDA_Plants_Database.csv')
species.columns = ['Species', 'Synonym Symbol', 'Scientific Name with Author',
       'State Common Name', 'Family']

pd.set_option('display.max_columns', None)
# print(data.columns)

total_found = data['num_Indivi'].sum()
sites = data['Site'].count()
print("\n", total_found, "total invasive species found across", sites, "sites")

simp_data = data.get(['Site', 'Species', 'num_Indivi'])

data_species = pd.merge(data, species, how='left')
#data_species = data_species.drop(data_species[data_species.num_Indivi == 0].index)

pivot = pd.pivot_table(data_species, values='num_Indivi', index=['Site'], columns=['Species'], aggfunc='sum')

#print(pivot.head())