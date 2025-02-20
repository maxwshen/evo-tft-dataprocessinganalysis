# 
from __future__ import division
import _config
import sys, os, fnmatch, datetime, subprocess
sys.path.append('/home/unix/maxwshen/')
import numpy as np
from collections import defaultdict
from mylib import util, compbio
import pandas as pd

# Default params
inp_dir_c = _config.OUT_PLACE + f'c2_combine/'
inp_dir_d = _config.OUT_PLACE + f'd_singlemuts/'
NAME = util.get_fn(__file__)
out_dir = _config.OUT_PLACE + NAME + '/'
util.ensure_dir_exists(out_dir)

design_df = pd.read_csv(_config.DATA_DIR + 'exp_design.csv')

params = {
  'major_thresholds': [5, 8, 10],
}

def get_muts(major_threshold):
  # Load from file output from Jupyter notebook
  # Format: {pos}{mut_aa}
  print(f'Using major mutation frequency threshold = {major_threshold}')
  major_muts_df = pd.read_csv(inp_dir_d + f'_above{major_threshold}.csv')
  major_muts = set(major_muts_df['Mutation'])
  return major_muts


##
# Primary
##
def get_majormuts(nm, major_threshold):
  major_muts = get_muts(major_threshold)

  mut_df = pd.read_csv(inp_dir_c + f'{nm}.csv', index_col = 0)

  print(f'Subsetting to {len(major_muts)} major mutations ...')
  mut_df['Mutation'] = mut_df['Position'].astype(str) + mut_df['Mutated amino acid']
  mut_df = mut_df[mut_df['Mutation'].isin(major_muts)]

  print('Pivoting ...')
  pv_df = mut_df.pivot(index = 'Read name', columns = 'Position', values = 'Mutated amino acid')
  pv_df = pv_df.fillna(value = '.')

  # Turn entries into '{pos} {aa}'
  for col in pv_df.columns:
    pv_df[col] = f'{col} ' + pv_df[col]

  pv_df['Full genotype'] = pv_df.apply(','.join, axis = 'columns')

  gdf = pv_df.groupby('Full genotype').size().reset_index(name = 'Count')
  gdf.to_csv(out_dir + f'{nm}_t{major_threshold}.csv')

  from collections import Counter
  import pickle
  counts = Counter(gdf['Count'])
  with open(out_dir + f'{nm}_t{major_threshold}.pkl', 'wb') as f:
    pickle.dump(counts, f)

  return

##
# qsub
##
def gen_qsubs():
  # Generate qsub shell scripts and commands for easy parallelization
  print('Generating qsub scripts...')
  qsubs_dir = _config.QSUBS_DIR + NAME + '/'
  util.ensure_dir_exists(qsubs_dir)
  qsub_commands = []

  num_scripts = 0
  for idx, row in design_df.iterrows():
    nm = row['Short name']

    for threshold in params['major_thresholds']:

      command = f'python {NAME}.py {nm} {threshold}'
      script_id = NAME.split('_')[0]

      # Write shell scripts
      sh_fn = qsubs_dir + f'q_{script_id}_{nm}_{threshold}.sh'
      with open(sh_fn, 'w') as f:
        f.write(f'#!/bin/bash\n{command}\n')
      num_scripts += 1

      # Write qsub commands
      qsub_commands.append(f'qsub -V -P regevlab -l h_rt=10:00:00,h_vmem=4G -wd {_config.SRC_DIR} {sh_fn} &')

  # Save commands
  commands_fn = qsubs_dir + '_commands.sh'
  with open(commands_fn, 'w') as f:
    f.write('\n'.join(qsub_commands))

  subprocess.check_output(f'chmod +x {commands_fn}', shell = True)

  print(f'Wrote {num_scripts} shell scripts to {qsubs_dir}')
  return

##
# Main
##
@util.time_dec
def main(args):
  print(NAME)
  
  # Function calls
  [nm, threshold] = args
  get_majormuts(nm, threshold)

  # for nm in ill_nms:
  #   print(nm)
  #   get_majormuts(nm)

  return


if __name__ == '__main__':
  if len(sys.argv) > 1:
    main(sys.argv[1:])
  else:
    gen_qsubs()
  # main([])
