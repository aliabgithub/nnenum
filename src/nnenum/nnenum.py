'''
nnenum vnnlib front end

usage: "python3 nnenum.py -o <onnx_file> -v <vnnlib_file> [-t timeout=None] [-f outfile=None] [-p processes] [-s settings=auto]"

Ali A. Bigdeli
June 2022
'''


import sys
import argparse

import numpy as np

from pathlib import Path

from nnenum.enumerate import enumerate_network
from nnenum.settings import Settings
from nnenum.result import Result
from nnenum.onnx_network import load_onnx_network_optimized, load_onnx_network
from nnenum.specification import Specification, DisjunctiveSpec
from nnenum.vnnlib import get_num_inputs_outputs, read_vnnlib_simple
import nnenum.setting_cat as setting_cat

def make_spec(vnnlib_filename, onnx_filename):
    '''make Specification

    returns a pair: (list of [box, Specification], inp_dtype)
    '''

    num_inputs, num_outputs, inp_dtype = get_num_inputs_outputs(onnx_filename)
    vnnlib_spec = read_vnnlib_simple(vnnlib_filename, num_inputs, num_outputs)

    rv = []

    for box, spec_list in vnnlib_spec:
        if len(spec_list) == 1:
            mat, rhs = spec_list[0]
            spec = Specification(mat, rhs)
        else:
            spec_obj_list = [Specification(mat, rhs) for mat, rhs in spec_list]
            spec = DisjunctiveSpec(spec_obj_list)

        rv.append((box, spec))

    return rv, inp_dtype

def set_control_settings():
    'set settings for smaller control benchmarks'

    Settings.TIMING_STATS = False
    Settings.PARALLEL_ROOT_LP = False
    Settings.SPLIT_IF_IDLE = False
    Settings.PRINT_OVERAPPROX_OUTPUT = False
    Settings.TRY_QUICK_OVERAPPROX = True

    Settings.CONTRACT_ZONOTOPE_LP = True
    Settings.CONTRACT_LP_OPTIMIZED = True
    Settings.CONTRACT_LP_TRACK_WITNESSES = True

    Settings.OVERAPPROX_BOTH_BOUNDS = False

    Settings.BRANCH_MODE = Settings.BRANCH_OVERAPPROX
    Settings.OVERAPPROX_GEN_LIMIT_MULTIPLIER = 1.5
    Settings.OVERAPPROX_LP_TIMEOUT = 0.02
    Settings.OVERAPPROX_MIN_GEN_LIMIT = 70

def set_exact_settings():
    'set settings for smaller control benchmarks'

    #Settings.TIMING_STATS = True
    Settings.TRY_QUICK_OVERAPPROX = False

    Settings.CONTRACT_ZONOTOPE_LP = True
    Settings.CONTRACT_LP_OPTIMIZED = True
    Settings.CONTRACT_LP_TRACK_WITNESSES = True

    Settings.OVERAPPROX_BOTH_BOUNDS = False

    Settings.BRANCH_MODE = Settings.BRANCH_EXACT

def set_image_settings():
    'set settings for larger image benchmarks'

    Settings.COMPRESS_INIT_BOX = True
    Settings.BRANCH_MODE = Settings.BRANCH_OVERAPPROX
    Settings.TRY_QUICK_OVERAPPROX = False
    
    Settings.OVERAPPROX_MIN_GEN_LIMIT = np.inf
    Settings.SPLIT_IF_IDLE = False
    Settings.OVERAPPROX_LP_TIMEOUT = np.inf
    #Settings.TIMING_STATS = True

    # contraction doesn't help in high dimensions
    #Settings.OVERAPPROX_CONTRACT_ZONO_LP = False
    Settings.CONTRACT_ZONOTOPE = False
    Settings.CONTRACT_ZONOTOPE_LP = False

def main():
    'main entry point'

    parser = argparse.ArgumentParser() # description is optional
    parser.add_argument('-o', '--onnx', type=str, required=True, help="relative path to onnx file")
    parser.add_argument('-v', '--vnnlib', type=str, required=True, help="relative path to vnnlib file")
    parser.add_argument('-t', '--timeout', default=None, help="timeout in seconds. default is no timeout")
    parser.add_argument('-f', '--outfile', type=str, default=None, help="filename the result save on, e.g.: out.txt, out.csv")
    parser.add_argument('-p', '--processes', type=int, help="number of processes to use")
    parser.add_argument('-s', '--settings', type=str, default="auto", help="settings to running the tool, it can be 'control' or 'image' or name of the dataset for more specified setting. default is auto")
    args = parser.parse_args()
    
    if args.onnx:
        onnx_filename = args.onnx
    
    if args.vnnlib:
        vnnlib_filename = args.vnnlib
    
    timeout = int(float(args.timeout)) if args.timeout else None
    
    outfile = args.outfile
    
    if args.processes:
        processes = args.processes
        Settings.NUM_PROCESSES = processes
    
    if args.settings:
        settings_str = args.settings
    else:
        settings_str = "auto"
        
    
    # if len(sys.argv) < 3:
    #     print('usage: "python3 nnenum.py <onnx_file> <vnnlib_file> [timeout=None] [outfile=None] [processes=<auto>]"')
    #     sys.exit(1)

    # onnx_filename = sys.argv[1]
    # vnnlib_filename = sys.argv[2]
    # timeout = None
    # outfile = None

    # if len(sys.argv) >= 4:
    #     timeout = float(sys.argv[3])

    # if len(sys.argv) >= 5:
    #     outfile = sys.argv[4]

    # if len(sys.argv) >= 6:
    #     processes = int(sys.argv[5])
    #     Settings.NUM_PROCESSES = processes

    # if len(sys.argv) >= 7:
    #     settings_str = sys.argv[6]
    # else:
    #     settings_str = "auto"

    ####################################
    ####################################
    ####################################
    # VNN-COMP 2022 SPECIFIC
    
    if Path(onnx_filename + ".converted").is_file():
        onnx_filename = onnx_filename + ".converted"
        print(f"NOTE: Using converted onnx path: {onnx_filename}")
        
    ####################################
    ####################################
    ####################################

    #
    spec_list, input_dtype = make_spec(vnnlib_filename, onnx_filename)

    try:
        network = load_onnx_network_optimized(onnx_filename)
    except:
        # cannot do optimized load due to unsupported layers
        network = load_onnx_network(onnx_filename)

    result_str = 'none' # gets overridden

    num_inputs = len(spec_list[0][0])

    if settings_str == "auto":
        if num_inputs < 700:
            set_control_settings()
        else:
            set_image_settings()
    elif settings_str == "cifar2020":
        set_image_settings()
    elif settings_str == "cifar_biasfield":
        set_image_settings()
        # Settings.LP_SOLVER = "Gurobi"
    elif settings_str == "mnist_fc":
        set_image_settings()
        Settings.LP_SOLVER = "Gurobi"
        Settings.OVERAPPROX_TYPES = [['deeppoly.area'], ['zono.area'], 
                                ['zono.area', 'zono.ybloat', 'zono.interval', 'deeppoly.area'],
                                ['zono.area', 'zono.ybloat', 'zono.interval', 'deeppoly.area', 'star.lp']] 
        Settings.QUICK_OVERAPPROX_TYPES = [['deeppoly.area'], ['zono.area'],
                                      ['zono.area', 'zono.ybloat', 'zono.interval', 'deeppoly.area']]
    elif settings_str in ["nn4sys", "2022_nn4sys", "2023_nn4sys", "nn4sys_2022", "nn4sys_2023"]:
        set_control_settings()
        Settings.LP_SOLVER = "Gurobi"
        # Settings.OVERAPPROX_TYPES = [['deeppoly.area'], ['zono.area'], 
        #                         ['zono.area', 'zono.ybloat', 'zono.interval', 'deeppoly.area'],
        #                         ['zono.area', 'zono.ybloat', 'zono.interval', 'deeppoly.area', 'star.lp']] 
        # Settings.QUICK_OVERAPPROX_TYPES = [['deeppoly.area'], ['zono.area'],
        #                               ['zono.area', 'zono.ybloat', 'zono.interval', 'deeppoly.area']]
    elif settings_str == "oval21":
        set_image_settings()
    elif settings_str == "reach_prob_density":
        set_control_settings()
    elif settings_str == "rl_benchmarks":
        set_control_settings()
    elif settings_str == "tllverifybench":
        set_control_settings()
        Settings.LP_SOLVER = "Gurobi"
    elif settings_str in ["vggnet16", "vggnet16_2022", "vggnet16_2023"]:
        set_image_settings()
    elif settings_str == "acasxu":
        set_control_settings()
    elif settings_str == "collins_rul_cnn":
        set_image_settings()
    elif settings_str == "cgan":
        set_image_settings()
    elif settings_str == "metaroom":
        set_image_settings()
        # Settings.LP_SOLVER = "Gurobi"
    elif settings_str == "control":
        set_control_settings()
    elif settings_str == "image":
        set_image_settings()
    elif settings_str == "exact":
        set_exact_settings()
    else:
        if num_inputs < 700:
            set_control_settings()
        else:
            set_image_settings()
    # else:
    #     assert settings_str == "exact"
    #     set_exact_settings()

    for init_box, spec in spec_list:
        init_box = np.array(init_box, dtype=input_dtype)

        if timeout is not None:
            if timeout <= 0:
                result_str = 'timeout'
                break

            Settings.TIMEOUT = timeout

        ####################################
        ####################################
        ####################################
        # VNN-COMP 2022 SPECIFIC
        Settings.TIMING_STATS = False
        Settings.PRINT_PROGRESS = False
        ####################################
        ####################################
        ####################################

        res = enumerate_network(init_box, network, spec)
        result_str = res.result_str

        if timeout is not None:
            # reduce timeout by the runtime
            timeout -= res.total_secs

        if result_str != "safe":
            break

    if result_str == "safe":
        result_str = "unsat"
    elif "unsafe" in result_str:
        result_str = "sat"

    if outfile is not None:
        with open(outfile, 'w', encoding="utf-8") as f:
            f.write(result_str)

            if result_str == "sat":
                # print counterexamples
                
                for i, x in enumerate(res.cinput):
                    if i == 0:
                        f.write('\n(')
                    else:
                        f.write('\n')
                    
                    f.write(f"(X_{i} {x})")

                ###########

                for i, y in enumerate(res.coutput):
                    f.write(f"\n(Y_{i} {y})")

                f.write(')')
            
    #print(result_str)

    if result_str == 'error':
        sys.exit(Result.results.index('error'))


if __name__ == '__main__':
    main()