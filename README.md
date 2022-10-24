# ddueruem
Pre Release Version for implementing static variable orderings evaluated in Eric's Master Thesis.

### Requirements
* Python 3.8+
* `make`
* `cmake`
* `glibc`
* `libgmp-dev`

### Usefull commands
That I should have known before using try-and-error to find them ... 

#### Initialization and Installation
```bash
./ddueruem.py --install smarch
```
```bash
./ddueruem.py --install cudd
```

### New SVOs
- pre_cl_size
- pre_cl_min_span
- fm_traversal_bf
- fm_traversal_df

### New Functionalities
- FORCE without timelimit (if timelimit is -1)
- If input file is xml, the corresponding file types`dimacs`, `uvl` and `sxfm` can be created automatically
- `.orders` and `.order` file now have own order_parser
- Build BDD from order file (for this args should not include any --svo ... )
- `initFeatureModels.sh` creates a folder `evalutation` in the workspace, containg all the feature models used in the SVO evaluation. Dir structure for every model is `evaluation/<model name>/<model name>.xml`

Added new SVOs and integrated them such that they can be used without any overhead for the user. 

#### Discussion
We have to discuss the following issues:
- `Pre_cl_family` and `fm_traversal` do not use the class `FM`. Refactoring to use it could be cumbersome and therefore it is discussable if this is really necessary.
- If we agree to the need of using the class `FM`, we should also consider to create a Class for the clusters used in Pre_CL
- `ddueruem.py` needs a slight rework because currently there are checks for file existens and if a file exists, e.g., building BDDs wont be executed. ~~Furthermore, there is the list `evals` which collects all filepaths to the evaluation models, filters them and sortes them according to file sizes. We could remove this or maybe introduce a flag like --evaluation.~~ New ideas are always welcome! 
- ~~Extend force such that it can handle xml files (create dimcas file if input is xml)~~ DONE


#### Usage Examples
Fresh start of evaluation for pre_cl_min_span
```bash
./init_featureModels.sh
./ddueruem.py --evaluation --svo pre_cl_min_span n:1
```
A certain model
```bash
./ddueruem.py examples/xml/mendonca_dis.xml --svo pre_cl_size n:1
```
**WARNING** pre_cl_.. is only compatible with `.xml` files which are not sxfm ~~and force is only compatible with `.dimacs` files at the moment~~

Build BDD without svo, from order file
```bash
./ddueruem.py parsed/out/mendonca_dis-pre_cl_size-1.orders --bdd cudd  lib_t:-1 dvo:off dump:True
```
