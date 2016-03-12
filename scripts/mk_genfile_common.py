# This file contains code that is common to
# both the Python build system and the CMake
# build system.
#
# The code here generally is involved in
# generating files needed by Z3 at build time.
#
# You should **not** import ``mk_util`` here
# to avoid having this code depend on the
# of the Python build system.
import os
import logging
import re
import sys

# Logger for this module
_logger = logging.getLogger(__name__)


###############################################################################
# Utility functions
###############################################################################
def check_dir_exists(output_dir):
    """
        Returns ``True`` if ``output_dir`` exists, otherwise
        returns ``False``.
    """
    if not os.path.isdir(output_dir):
        _logger.error('"{}" is not an existing directory'.format(output_dir))
        return False
    return True

def check_files_exist(files):
    assert isinstance(files, list)
    for f in files:
        if not os.path.exists(f):
            _logger.error('"{}" does not exist'.format(f))
            return False
    return True

###############################################################################
# Functions for generating constant declarations for language bindings
###############################################################################

def mk_z3consts_py_internal(api_files, output_dir):
    """
        Generate ``z3consts.py`` from the list of API header files
        in ``api_files`` and write the output file into
        the ``output_dir`` directory

        Returns the path to the generated file.
    """
    assert os.path.isdir(output_dir)
    assert isinstance(api_files, list)

    blank_pat      = re.compile("^ *\r?$")
    comment_pat    = re.compile("^ *//.*$")
    typedef_pat    = re.compile("typedef enum *")
    typedef2_pat   = re.compile("typedef enum { *")
    openbrace_pat  = re.compile("{ *")
    closebrace_pat = re.compile("}.*;")

    z3consts  = open(os.path.join(output_dir, 'z3consts.py'), 'w')
    z3consts_output_path = z3consts.name
    z3consts.write('# Automatically generated file\n\n')
    for api_file in api_files:
        api = open(api_file, 'r')

        SEARCHING  = 0
        FOUND_ENUM = 1
        IN_ENUM    = 2

        mode    = SEARCHING
        decls   = {}
        idx     = 0

        linenum = 1
        for line in api:
            m1 = blank_pat.match(line)
            m2 = comment_pat.match(line)
            if m1 or m2:
                # skip blank lines and comments
                linenum = linenum + 1
            elif mode == SEARCHING:
                m = typedef_pat.match(line)
                if m:
                    mode = FOUND_ENUM
                m = typedef2_pat.match(line)
                if m:
                    mode = IN_ENUM
                    decls = {}
                    idx   = 0
            elif mode == FOUND_ENUM:
                m = openbrace_pat.match(line)
                if m:
                    mode  = IN_ENUM
                    decls = {}
                    idx   = 0
                else:
                    assert False, "Invalid %s, line: %s" % (api_file, linenum)
            else:
                assert mode == IN_ENUM
                words = re.split('[^\-a-zA-Z0-9_]+', line)
                m = closebrace_pat.match(line)
                if m:
                    name = words[1]
                    z3consts.write('# enum %s\n' % name)
                    for k in decls:
                        i = decls[k]
                        z3consts.write('%s = %s\n' % (k, i))
                    z3consts.write('\n')
                    mode = SEARCHING
                elif len(words) <= 2:
                    assert False, "Invalid %s, line: %s" % (api_file, linenum)
                else:
                    if words[2] != '':
                        if len(words[2]) > 1 and words[2][1] == 'x':
                            idx = int(words[2], 16)
                        else:
                            idx = int(words[2])
                    decls[words[1]] = idx
                    idx = idx + 1
            linenum = linenum + 1
        api.close()
    z3consts.close()
    return z3consts_output_path

###############################################################################
# Functions for generating a "module definition file" for MSVC
###############################################################################

def mk_def_file_internal(defname, dll_name, export_header_files):
    """
      Writes to a module definition file to a file named ``defname``.

      ``dll_name`` is the name of the dll (without the ``.dll`` suffix).
      ``export_header_file`` is a list of header files to scan for symbols
      to include in the module definition file.
    """
    assert isinstance(export_header_files, list)
    pat1 = re.compile(".*Z3_API.*")
    fout = open(defname, 'w')
    fout.write('LIBRARY "%s"\nEXPORTS\n' % dll_name)
    num = 1
    for export_header_file in export_header_files:
        api = open(export_header_file, 'r')
        for line in api:
            m = pat1.match(line)
            if m:
                words = re.split('\W+', line)
                i = 0
                for w in words:
                    if w == 'Z3_API':
                        f = words[i+1]
                        fout.write('\t%s @%s\n' % (f, num))
                    i = i + 1
                num = num + 1
        api.close()
    fout.close()

###############################################################################
# Functions for generating ``gparams_register_modules.cpp``
###############################################################################
def mk_gparams_register_modules_internal(component_src_dirs, path):
    """
        Generate a ``gparams_register_modules.cpp`` file in the directory ``path``.
        Returns the path to the generated file.

        This file implements the procedure

        ```
        void gparams_register_modules()
        ```

        This procedure is invoked by gparams::init()
    """
    assert isinstance(component_src_dirs, list)
    assert check_dir_exists(path)
    cmds = []
    mod_cmds = []
    mod_descrs = []
    fullname = os.path.join(path, 'gparams_register_modules.cpp')
    fout  = open(fullname, 'w')
    fout.write('// Automatically generated file.\n')
    fout.write('#include"gparams.h"\n')
    reg_pat = re.compile('[ \t]*REG_PARAMS\(\'([^\']*)\'\)')
    reg_mod_pat = re.compile('[ \t]*REG_MODULE_PARAMS\(\'([^\']*)\', *\'([^\']*)\'\)')
    reg_mod_descr_pat = re.compile('[ \t]*REG_MODULE_DESCRIPTION\(\'([^\']*)\', *\'([^\']*)\'\)')
    for component_src_dir in component_src_dirs:
        h_files = filter(lambda f: f.endswith('.h') or f.endswith('.hpp'), os.listdir(component_src_dir))
        for h_file in h_files:
            added_include = False
            fin = open(os.path.join(component_src_dir, h_file), 'r')
            for line in fin:
                m = reg_pat.match(line)
                if m:
                    if not added_include:
                        added_include = True
                        fout.write('#include"%s"\n' % h_file)
                    cmds.append((m.group(1)))
                m = reg_mod_pat.match(line)
                if m:
                    if not added_include:
                        added_include = True
                        fout.write('#include"%s"\n' % h_file)
                    mod_cmds.append((m.group(1), m.group(2)))
                m = reg_mod_descr_pat.match(line)
                if m:
                    mod_descrs.append((m.group(1), m.group(2)))
            fin.close()
    fout.write('void gparams_register_modules() {\n')
    for code in cmds:
        fout.write('{ param_descrs d; %s(d); gparams::register_global(d); }\n' % code)
    for (mod, code) in mod_cmds:
        fout.write('{ param_descrs * d = alloc(param_descrs); %s(*d); gparams::register_module("%s", d); }\n' % (code, mod))
    for (mod, descr) in mod_descrs:
        fout.write('gparams::register_module_descr("%s", "%s");\n' % (mod, descr))
    fout.write('}\n')
    fout.close()
    return fullname

###############################################################################
# Functions/data structures for generating ``install_tactics.cpp``
###############################################################################

def mk_install_tactic_cpp_internal(component_src_dirs, path):
    """
        Generate a ``install_tactics.cpp`` file in the directory ``path``.
        Returns the path the generated file.

        This file implements the procedure

        ```
        void install_tactics(tactic_manager & ctx)
        ```

        It installs all tactics found in the given component directories
        ``component_src_dirs`` The procedure looks for ``ADD_TACTIC`` commands
        in the ``.h``  and ``.hpp`` files of these components.
    """
    ADD_TACTIC_DATA = []
    ADD_PROBE_DATA = []
    def ADD_TACTIC(name, descr, cmd):
        ADD_TACTIC_DATA.append((name, descr, cmd))

    def ADD_PROBE(name, descr, cmd):
        ADD_PROBE_DATA.append((name, descr, cmd))

    exec_globals = {
        'ADD_TACTIC': ADD_TACTIC,
        'ADD_PROBE': ADD_PROBE,
    }

    assert isinstance(component_src_dirs, list)
    assert check_dir_exists(path)
    fullname = os.path.join(path, 'install_tactic.cpp')
    fout  = open(fullname, 'w')
    fout.write('// Automatically generated file.\n')
    fout.write('#include"tactic.h"\n')
    fout.write('#include"tactic_cmds.h"\n')
    fout.write('#include"cmd_context.h"\n')
    tactic_pat   = re.compile('[ \t]*ADD_TACTIC\(.*\)')
    probe_pat    = re.compile('[ \t]*ADD_PROBE\(.*\)')
    for component_src_dir in component_src_dirs:
        h_files = filter(lambda f: f.endswith('.h') or f.endswith('.hpp'), os.listdir(component_src_dir))
        for h_file in h_files:
            added_include = False
            fin = open(os.path.join(component_src_dir, h_file), 'r')
            for line in fin:
                if tactic_pat.match(line):
                    if not added_include:
                        added_include = True
                        fout.write('#include"%s"\n' % h_file)
                    try:
                        exec(line.strip('\n '), exec_globals)
                    except Exception as e:
                        _logger.error("Failed processing ADD_TACTIC command at '{}'\n{}".format(
                            fullname, line))
                        raise e
                if probe_pat.match(line):
                    if not added_include:
                        added_include = True
                        fout.write('#include"%s"\n' % h_file)
                    try:
                        exec(line.strip('\n '), exec_globals)
                    except Exception as e:
                        _logger.error("Failed processing ADD_PROBE command at '{}'\n{}".format(
                            fullname, line))
                        raise e
            fin.close()
    # First pass will just generate the tactic factories
    idx = 0
    for data in ADD_TACTIC_DATA:
        fout.write('MK_SIMPLE_TACTIC_FACTORY(__Z3_local_factory_%s, %s);\n' % (idx, data[2]))
        idx = idx + 1
    fout.write('#define ADD_TACTIC_CMD(NAME, DESCR, FACTORY) ctx.insert(alloc(tactic_cmd, symbol(NAME), DESCR, alloc(FACTORY)))\n')
    fout.write('#define ADD_PROBE(NAME, DESCR, PROBE) ctx.insert(alloc(probe_info, symbol(NAME), DESCR, PROBE))\n')
    fout.write('void install_tactics(tactic_manager & ctx) {\n')
    idx = 0
    for data in ADD_TACTIC_DATA:
        fout.write('  ADD_TACTIC_CMD("%s", "%s", __Z3_local_factory_%s);\n' % (data[0], data[1], idx))
        idx = idx + 1
    for data in ADD_PROBE_DATA:
        fout.write('  ADD_PROBE("%s", "%s", %s);\n' % data)
    fout.write('}\n')
    fout.close()
    return fullname

###############################################################################
# Functions for generating ``mem_initializer.cpp``
###############################################################################

def mk_mem_initializer_cpp_internal(component_src_dirs, path):
    """
        Generate a ``mem_initializer.cpp`` file in the directory ``path``.
        Returns the path to the generated file.

        This file implements the procedures

        ```
        void mem_initialize()
        void mem_finalize()
        ```

       These procedures are invoked by the Z3 memory_manager
    """
    assert isinstance(component_src_dirs, list)
    assert check_dir_exists(path)
    initializer_cmds = []
    finalizer_cmds   = []
    fullname = os.path.join(path, 'mem_initializer.cpp')
    fout  = open(fullname, 'w')
    fout.write('// Automatically generated file.\n')
    initializer_pat      = re.compile('[ \t]*ADD_INITIALIZER\(\'([^\']*)\'\)')
    # ADD_INITIALIZER with priority
    initializer_prio_pat = re.compile('[ \t]*ADD_INITIALIZER\(\'([^\']*)\',[ \t]*(-?[0-9]*)\)')
    finalizer_pat        = re.compile('[ \t]*ADD_FINALIZER\(\'([^\']*)\'\)')
    for component_src_dir in component_src_dirs:
        h_files = filter(lambda f: f.endswith('.h') or f.endswith('.hpp'), os.listdir(component_src_dir))
        for h_file in h_files:
            added_include = False
            fin = open(os.path.join(component_src_dir, h_file), 'r')
            for line in fin:
                m = initializer_pat.match(line)
                if m:
                    if not added_include:
                        added_include = True
                        fout.write('#include"%s"\n' % h_file)
                    initializer_cmds.append((m.group(1), 0))
                m = initializer_prio_pat.match(line)
                if m:
                    if not added_include:
                        added_include = True
                        fout.write('#include"%s"\n' % h_file)
                    initializer_cmds.append((m.group(1), int(m.group(2))))
                m = finalizer_pat.match(line)
                if m:
                    if not added_include:
                        added_include = True
                        fout.write('#include"%s"\n' % h_file)
                    finalizer_cmds.append(m.group(1))
            fin.close()
    initializer_cmds.sort(key=lambda tup: tup[1])
    fout.write('void mem_initialize() {\n')
    for (cmd, prio) in initializer_cmds:
        fout.write(cmd)
        fout.write('\n')
    fout.write('}\n')
    fout.write('void mem_finalize() {\n')
    for cmd in finalizer_cmds:
        fout.write(cmd)
        fout.write('\n')
    fout.write('}\n')
    fout.close()
    return fullname

###############################################################################
# Functions for generating ``database.h``
###############################################################################

def mk_pat_db_internal(inputFilePath, outputFilePath):
    """
        Generate ``g_pattern_database[]`` declaration header file.
    """
    with open(inputFilePath, 'r') as fin:
        with open(outputFilePath, 'w') as fout:
            fout.write('static char const g_pattern_database[] =\n')
            for line in fin:
                fout.write('"%s\\n"\n' % line.strip('\n'))
            fout.write(';\n')

###############################################################################
# Functions and data structures for generating ``*_params.hpp`` files from
# ``*.pyg`` files
###############################################################################

UINT   = 0
BOOL   = 1
DOUBLE = 2
STRING = 3
SYMBOL = 4
UINT_MAX = 4294967295

TYPE2CPK = { UINT : 'CPK_UINT', BOOL : 'CPK_BOOL',  DOUBLE : 'CPK_DOUBLE',  STRING : 'CPK_STRING',  SYMBOL : 'CPK_SYMBOL' }
TYPE2CTYPE = { UINT : 'unsigned', BOOL : 'bool', DOUBLE : 'double', STRING : 'char const *', SYMBOL : 'symbol' }
TYPE2GETTER = { UINT : 'get_uint', BOOL : 'get_bool', DOUBLE : 'get_double', STRING : 'get_str',  SYMBOL : 'get_sym' }

def pyg_default(p):
    if p[1] == BOOL:
        if p[2]:
            return "true"
        else:
            return "false"
    return p[2]

def pyg_default_as_c_literal(p):
    if p[1] == BOOL:
        if p[2]:
            return "true"
        else:
            return "false"
    elif p[1] == STRING:
        return '"%s"' % p[2]
    elif p[1] == SYMBOL:
        return 'symbol("%s")' % p[2]
    elif p[1] == UINT:
        return '%su' % p[2]
    else:
        return p[2]

def to_c_method(s):
    return s.replace('.', '_')


def max_memory_param():
    return ('max_memory', UINT, UINT_MAX, 'maximum amount of memory in megabytes')

def max_steps_param():
    return ('max_steps', UINT, UINT_MAX, 'maximum number of steps')

def mk_hpp_from_pyg(pyg_file, output_dir):
    """
        Generates the corresponding header file for the input pyg file
        at the path ``pyg_file``. The file is emitted into the directory
        ``output_dir``.

        Returns the path to the generated file
    """
    CURRENT_PYG_HPP_DEST_DIR = output_dir
    # Note OUTPUT_HPP_FILE cannot be a string as we need a mutable variable
    # for the nested function to modify
    OUTPUT_HPP_FILE = [ ]
    # The function below has been nested so that it can use closure to capture
    # the above variables that aren't global but instead local to this
    # function. This avoids use of global state which makes this function safer.
    def def_module_params(module_name, export, params, class_name=None, description=None):
        dirname = CURRENT_PYG_HPP_DEST_DIR
        assert(os.path.exists(dirname))
        if class_name is None:
            class_name = '%s_params' % module_name
        hpp = os.path.join(dirname, '%s.hpp' % class_name)
        out = open(hpp, 'w')
        out.write('// Automatically generated file\n')
        out.write('#ifndef __%s_HPP_\n' % class_name.upper())
        out.write('#define __%s_HPP_\n' % class_name.upper())
        out.write('#include"params.h"\n')
        if export:
            out.write('#include"gparams.h"\n')
        out.write('struct %s {\n' % class_name)
        out.write('  params_ref const & p;\n')
        if export:
            out.write('  params_ref g;\n')
        out.write('  %s(params_ref const & _p = params_ref::get_empty()):\n' % class_name)
        out.write('     p(_p)')
        if export:
            out.write(', g(gparams::get_module("%s"))' % module_name)
        out.write(' {}\n')
        out.write('  static void collect_param_descrs(param_descrs & d) {\n')
        for param in params:
            out.write('    d.insert("%s", %s, "%s", "%s","%s");\n' % (param[0], TYPE2CPK[param[1]], param[3], pyg_default(param), module_name))
        out.write('  }\n')
        if export:
            out.write('  /*\n')
            out.write("     REG_MODULE_PARAMS('%s', '%s::collect_param_descrs')\n" % (module_name, class_name))
            if description is not None:
                out.write("     REG_MODULE_DESCRIPTION('%s', '%s')\n" % (module_name, description))
            out.write('  */\n')
        # Generated accessors
        for param in params:
            if export:
                out.write('  %s %s() const { return p.%s("%s", g, %s); }\n' %
                          (TYPE2CTYPE[param[1]], to_c_method(param[0]), TYPE2GETTER[param[1]], param[0], pyg_default_as_c_literal(param)))
            else:
                out.write('  %s %s() const { return p.%s("%s", %s); }\n' %
                          (TYPE2CTYPE[param[1]], to_c_method(param[0]), TYPE2GETTER[param[1]], param[0], pyg_default_as_c_literal(param)))
        out.write('};\n')
        out.write('#endif\n')
        out.close()
        OUTPUT_HPP_FILE.append(hpp)

    # Globals to use when executing the ``.pyg`` file.
    pyg_globals = {
        'UINT' : UINT,
        'BOOL' : BOOL,
        'DOUBLE' : DOUBLE,
        'STRING' : STRING,
        'SYMBOL' : SYMBOL,
        'UINT_MAX' : UINT_MAX,
        'max_memory_param' : max_memory_param,
        'max_steps_param' : max_steps_param,
        # Note that once this function is enterred that function
        # executes with respect to the globals of this module and
        # not the globals defined here
        'def_module_params' : def_module_params,
    }
    with open(pyg_file, 'r') as fh:
        exec(fh.read() + "\n", pyg_globals, None)
    assert len(OUTPUT_HPP_FILE) == 1
    return OUTPUT_HPP_FILE[0]
