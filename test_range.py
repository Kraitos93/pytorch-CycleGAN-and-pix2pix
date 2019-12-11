import test
import os
import sys
from options.test_options import TestOptions

def main(model_name, epoch_from, epoch_to, num_test):
    for i in range(epoch_from, epoch_to):
        os.system("python3 test.py --dataroot ./datasets/bottles/%s --mode cycle_gan --epoch %i --name %s_cyclegan --num_test %s" 
        % (model_name, i, model_name, num_test))  
        
if __name__ == "__main__":
    opt = TestOptions().parse()
    main(opt.range_name, opt.epoch_from, opt.epoch_to, opt.num_test)