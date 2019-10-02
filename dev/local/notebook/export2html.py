#AUTOGENERATED! DO NOT EDIT! File to edit: dev/93_notebook_export2html.ipynb (unless otherwise specified).

__all__ = ['remove_widget_state', 'hide_cells', 'clean_exports', 'treat_backticks', 'convert_links', 'add_jekyll_notes',
           'copy_images', 'remove_hidden', 'find_default_level', 'add_show_docs', 'remove_fake_headers', 'remove_empty',
           'get_metadata', 'ExecuteShowDocPreprocessor', 'execute_nb', 'process_cells', 'process_cell', 'notebook_path',
           'convert_nb', 'convert_post']

#Cell
from ..imports import *
from ..core import compose
from ..test import *
from .export import *
from .showdoc import *
import nbformat
from notebook import notebookapp
from nbconvert.preprocessors import ExecutePreprocessor, Preprocessor
from nbconvert import HTMLExporter,MarkdownExporter
from nbformat.sign import NotebookNotary
from traitlets.config import Config

#Cell
def remove_widget_state(cell):
    "Remove widgets in the output of `cells`"
    if cell['cell_type'] == 'code' and 'outputs' in cell:
        cell['outputs'] = [l for l in cell['outputs']
                           if not ('data' in l and 'application/vnd.jupyter.widget-view+json' in l.data)]
    return cell

#Cell
# Matches any cell that has a `show_doc` or an `#export` in it
_re_cell_to_hide = r's*show_doc\(|^\s*#\s*export\s+'

#Cell
def hide_cells(cell):
    "Hide `cell` that need to be hidden"
    if check_re(cell, _re_cell_to_hide):  cell['metadata'] = {'hide_input': True}
    return cell

#Cell
# Matches any line containing an #exports
_re_exports = re.compile(r'^#\s*exports[^\n]*\n')

#Cell
def clean_exports(cell):
    "Remove exports flag from `cell`"
    cell['source'] = _re_exports.sub('', cell['source'])
    return cell

#Cell
def treat_backticks(cell):
    "Add links to backticks words in `cell`"
    if cell['cell_type'] == 'markdown': cell['source'] = add_doc_links(cell['source'])
    return cell

#Cell
_re_nb_link = re.compile(r"""
# Catches any link to a local notebook and keeps the title in group 1, the link without .ipynb in group 2
\[          # Opening [
([^\]]*)    # Catching group for any character except ]
\]\(        # Closing ], opening (
([^http]    # Catching group that must not begin by html (local notebook)
[^\)]*)     # and containing anything but )
.ipynb\)    # .ipynb and closing )
""", re.VERBOSE)

#Cell
def convert_links(cell):
    "Convert the .ipynb links to .html"
    if cell['cell_type'] == 'markdown':
        cell['source'] = _re_nb_link.sub(r'[\1](\2.html)', cell['source'])
    return cell

#Cell
_re_block_notes = re.compile(r"""
# Catches any pattern > Title: content with title in group 1 and content in group 2
^>\s*      # > followed by any number of whitespace
([^:]*)   # Catching group for any character but :
:\s*      # : then any number of whitespace
([^\n]*)  # Catching group for anything but a new line character
(?:\n|$)  # Non-catching group for either a new line or the end of the text
""", re.VERBOSE)

#Cell
def add_jekyll_notes(cell):
    "Convert block quotes to jekyll notes in `cell`"
    t2style = {'Note': 'info', 'Warning': 'danger', 'Important': 'warning'}
    def _inner(m):
        title,text = m.groups()
        style = t2style.get(title, None)
        if style is None: return f"> {m.groups()[0]}: {m.groups()[1]}"
        res = f'<div markdown="span" class="alert alert-{style}" role="alert">'
        return res + f'<i class="fa fa-{style}-circle"></i> <b>{title}: </b>{text}</div>'
    if cell['cell_type'] == 'markdown':
        cell['source'] = _re_block_notes.sub(_inner, cell['source'])
    return cell

#Cell
_re_image = re.compile(r"""
# Catches any image file used, either with `![alt](image_file)` or `<img src="image_file">`
^!\[        #   Beginning of line (since re.MULTILINE is passed) followed by ![
[^\]]*      #   Anything but ]
\]\(        #   Closing ] and opening (
([^\)]*)    #   Catching block with any character but )
\)          #   Closing )
|           # OR
<img\ src="  #   <img src="
([^"]*)     #   Catching block with any character except "
"           #   Closing
""", re.MULTILINE | re.VERBOSE)

#Cell
def copy_images(cell, fname, dest):
    if cell['cell_type'] == 'markdown' and _re_image.search(cell['source']):
        grps = _re_image.search(cell['source']).groups()
        src = grps[0] or grps[1]
        os.makedirs((Path(dest)/src).parent, exist_ok=True)
        shutil.copy(Path(fname).parent/src, Path(dest)/src)
    return cell

#Cell
#Matches any cell with #hide or #default_exp or #default_cls_lvl
_re_cell_to_remove = re.compile(r'^\s*#\s*(hide|default_exp|default_cls_lvl)\s+')

#Cell
def remove_hidden(cells):
    "Remove in `cells` the ones with a flag `#hide` or `#default_exp`"
    return [c for c in cells if _re_cell_to_remove.search(c['source']) is None]

#Cell
_re_default_cls_lvl = re.compile(r"""
^               # Beginning of line (since re.MULTILINE is passed)
\s*\#\s*        # Any number of whitespace, #, any number of whitespace
default_cls_lvl # default_cls_lvl
\s*             # Any number of whitespace
(\d*)           # Catching group for any number of digits
\s*$            # Any number of whitespace and end of line (since re.MULTILINE is passed)
""", re.IGNORECASE | re.MULTILINE | re.VERBOSE)

#Cell
def find_default_level(cells):
    "Find in `cells` the default export module."
    for cell in cells:
        tst = check_re(cell, _re_default_cls_lvl)
        if tst: return int(tst.groups()[0])
    return 2

#Cell
#Find a cell with #export(s)
_re_export = re.compile(r'^\s*#\s*exports?\s*', re.IGNORECASE | re.MULTILINE)
_re_show_doc = re.compile(r"""
# First one catches any cell with a #export or #exports, second one catches any show_doc and get the first argument in group 1
show_doc     # show_doc
\s*\(\s*     # Any number of whitespace, opening (, any number of whitespace
([^,\)\s]*)  # Catching group for any character but a comma, a closing ) or a whitespace
[,\)\s]      # A comma, a closing ) or a whitespace
""", re.MULTILINE | re.VERBOSE)

#Cell
def _show_doc_cell(name, cls_lvl=None):
    return {'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': f"show_doc({name}{'' if cls_lvl is None else f', default_cls_level={cls_lvl}'})"}

def add_show_docs(cells, cls_lvl=None):
    "Add `show_doc` for each exported function or class"
    documented = [_re_show_doc.search(cell['source']).groups()[0] for cell in cells
                  if cell['cell_type']=='code' and _re_show_doc.search(cell['source']) is not None]
    res = []
    for cell in cells:
        res.append(cell)
        if check_re(cell, _re_export):
            names = export_names(cell['source'], func_only=True)
            for n in names:
                if n not in documented: res.append(_show_doc_cell(n, cls_lvl=cls_lvl))
    return res

#Cell
_re_fake_header = re.compile(r"""
# Matches any fake header (one that ends with -)
\#+    # One or more #
\s+    # One or more of whitespace
.*     # Any char
-\s*   # A dash followed by any number of white space
$      # End of text
""", re.VERBOSE)

#Cell
def remove_fake_headers(cells):
    "Remove in `cells` the fake header"
    return [c for c in cells if c['cell_type']=='code' or _re_fake_header.search(c['source']) is None]

#Cell
def remove_empty(cells):
    "Remove in `cells` the empty cells"
    return [c for c in cells if len(c['source']) >0]

#Cell
_re_title_summary = re.compile(r"""
# Catches the title and summary of the notebook, presented as # Title > summary, with title in group 1 and summary in group 2
^\s*       # Beginning of text followe by any number of whitespace
\#\s+      # # followed by one or more of whitespace
([^\n]*)   # Catching group for any character except a new line
\n+        # One or more new lines
>\s*       # > followed by any number of whitespace
([^\n]*)   # Catching group for any character except a new line
""", re.VERBOSE)

_re_properties = re.compile(r"""
^-\s+      # Beginnig of a line followed by - and at least one space
(.*?)      # Any pattern (shortest possible)
\s*:\s*    # Any number of whitespace, :, any number of whitespace
(.*?)$     # Any pattern (shortest possible) then end of line
""", re.MULTILINE | re.VERBOSE)

#Cell
def get_metadata(cells):
    "Find the cell with title and summary in `cells`."
    for i,cell in enumerate(cells):
        if cell['cell_type'] == 'markdown':
            match = _re_title_summary.match(cell['source'])
            if match:
                cells.pop(i)
                attrs = {k:v for k,v in _re_properties.findall(cell['source'])}
                return {'keywords': 'fastai',
                        'summary' : match.groups()[1],
                        'title'   : match.groups()[0],
                        **attrs}
    return {'keywords': 'fastai',
            'summary' : 'summary',
            'title'   : 'Title'}

#Cell
#Catches any cell with a show_doc or an import from local
_re_cell_to_execute = re.compile(r"^\s*show_doc\(([^\)]*)\)|^from local\.", re.MULTILINE)

#Cell
class ExecuteShowDocPreprocessor(ExecutePreprocessor):
    "An `ExecutePreprocessor` that only executes `show_doc` and `import` cells"
    def preprocess_cell(self, cell, resources, index):
        if 'source' in cell and cell['cell_type'] == "code":
            if _re_cell_to_execute.search(cell['source']):
                return super().preprocess_cell(cell, resources, index)
        return cell, resources

#Cell
def _import_show_doc_cell(mod=None, name=None):
    "Add an import show_doc cell + deal with the __file__ hack if necessary."
    source = f"#export\nfrom local.notebook.showdoc import show_doc"
    if mod:  source += f"\nfrom local.{mod} import *"
    if name: source += f"\nfrom pathlib import Path\n__file__ = {name}"
    return {'cell_type': 'code',
            'execution_count': None,
            'metadata': {'hide_input': True},
            'outputs': [],
            'source': source}

def execute_nb(nb, mod=None, metadata=None, show_doc_only=True, name=None):
    "Execute `nb` (or only the `show_doc` cells) with `metadata`"
    nb['cells'].insert(0, _import_show_doc_cell(mod, name))
    ep_cls = ExecuteShowDocPreprocessor if show_doc_only else ExecutePreprocessor
    ep = ep_cls(timeout=600, kernel_name='python3')
    metadata = metadata or {}
    pnb = nbformat.from_dict(nb)
    ep.preprocess(pnb, metadata)
    return pnb

#Cell
def _exporter(markdown=False):
    cfg = Config()
    exporter = (HTMLExporter,MarkdownExporter)[markdown](cfg)
    exporter.exclude_input_prompt=True
    exporter.exclude_output_prompt=True
    exporter.template_file = ('jekyll.tpl','jekyll-md.tpl')[markdown]
    exporter.template_path.append(str(Path(__file__).parent))
    return exporter

#Cell
process_cells = [remove_fake_headers, remove_hidden, remove_empty]
process_cell  = [hide_cells, remove_widget_state, add_jekyll_notes, convert_links]

#Cell
_re_file = re.compile(r"""
^__file__   # __file__ at the beginning of a line (since re.MULTILINE is passed)
\s*=\s*   # Any number of whitespace, =, any number of whitespace
(\S*)     # Catching group for any non-whitespace characters
\s*$      # Any number of whitespace then the end of line
""", re.MULTILINE | re.VERBOSE)

#Cell
def _find_file(cells):
    "Find in `cells` if a __file__ is defined."
    for cell in cells:
        if cell['cell_type']=='code' and _re_file.search(cell['source']):
            return _re_file.search(cell['source']).groups()[0]

#Cell
def notebook_path():
    "Returns the absolute path of the Notebook or None if it cannot be determined"
    #NOTE: works only when the security is token-based or there is no password
    kernel_id = Path(ipykernel.get_connection_file()).stem.split('-', 1)[1]
    for srv in notebookapp.list_running_servers():
        try:
            sessions = json.load(urlopen(f"{srv['url']}api/sessions{srv['token']}"))
            return next(Path(srv['notebook_dir'])/sess['notebook']['path']
                        for sess in sessions if sess['kernel']['id']==kernel_id)
        except: pass  # There may be stale entries in the runtime directory

#Cell
def convert_nb(fname, dest_path='docs'):
    "Convert a notebook `fname` to html file in `dest_path`."
    fname = Path(fname).absolute()
    nb = read_nb(fname)
    cls_lvl = find_default_level(nb['cells'])
    _name = _find_file(nb['cells'])
    mod = find_default_export(nb['cells'])
    nb['cells'] = compose(*process_cells,partial(add_show_docs, cls_lvl=cls_lvl))(nb['cells'])
    nb['cells'] = [compose(partial(copy_images, fname=fname, dest=dest_path), *process_cell, treat_backticks)(c)
                    for c in nb['cells']]
    fname = Path(fname).absolute()
    dest_name = '.'.join(fname.with_suffix('.html').name.split('_')[1:])
    meta_jekyll = get_metadata(nb['cells'])
    meta_jekyll['nb_path'] = f'{fname.parent.name}/{fname.name}'
    nb = execute_nb(nb, mod=mod, name=_name)
    nb['cells'] = [clean_exports(c) for c in nb['cells']]
    #print(f'{dest_path}/{dest_name}')
    with open(f'{dest_path}/{dest_name}','w') as f:
        #res = _exporter().from_notebook_node(nb, resources=meta_jekyll)[0]
        #print(res)
        f.write(_exporter().from_notebook_node(nb, resources=meta_jekyll)[0])

#Cell
def convert_post(fname, dest_path='posts'):
    "Convert a notebook `fname` to blog post markdown in `dest_path`."
    fname = Path(fname).absolute()
    nb = read_nb(fname)
    meta_jekyll = get_metadata(nb['cells'])
    nb['cells'] = compose(*process_cells)(nb['cells'])
    nb['cells'] = [compose(*process_cell)(c) for c in nb['cells']]
    fname = Path(fname).absolute()
    dest_name = fname.with_suffix('.md').name
    exp = _exporter(markdown=True)
    with (Path(dest_path)/dest_name).open('w') as f:
        f.write(exp.from_notebook_node(nb, resources=meta_jekyll)[0])