import os
import re
import shutil
import pypdf
import pathlib
import arxiv

from pdfrw import PdfReader, PdfWriter
from pdfrw.findobjs import trivial_xobjs, wrap_object, find_objects
from pdfrw.objects import PdfDict, PdfArray, PdfName

class readarxiv():
    def __init__(self, arxiv_id):
        self.arxiv_id = arxiv_id
        self.dirpath = pathlib.Path(f'./{arxiv_id}')
        self.filename = f'{arxiv_id}.pdf'
        self.src_path = self.dirpath / self.filename
        self.out_path = self.dirpath / ('out_' + self.filename)
        self.figure_path = self.dirpath / 'slide' / 'figures'
        
        self.figure_path.mkdir(parents=True, exist_ok=True)

    def get_paper(self):
        paper = next(arxiv.Search(id_list=[self.arxiv_id]).results())
        self.url = paper.entry_id
        self.authors = [str(auth) for auth in paper.authors]
        self.title = re.sub('[\n|\\\\]', ' ', paper.title)
        self.abstract = re.sub('\s', ' ', re.sub('[\n|\\\\]', ' ', paper.summary))
        paper.download_pdf(dirpath=self.dirpath, filename=self.filename)

    def split_pdf_pages(self):
        src_pdf = pypdf.PdfReader(self.out_path)
        for i, page in enumerate(src_pdf.pages):
            dst_pdf = pypdf.PdfWriter()
            dst_pdf.add_page(page)
            dst_pdf.write(self.figure_path / f'figure_{i+1}.pdf')

    def get_figures(self):
        WIDTH = 8.5*72
        MARGIN = 0.5*72

        pdf = PdfReader(self.src_path)
        objects = []
        for xobj in list(find_objects(pdf.pages)):
            if xobj.Type==PdfName.XObject and xobj.Subtype==PdfName.Form:
                if '/PTEX.FileName' in xobj:
                    wrapped = wrap_object(xobj, WIDTH, MARGIN)
                    objects.append(wrapped)

        if not objects:
            raise IndexError("No XObjects found")
        writer = PdfWriter(self.out_path)
        writer.addpages(objects)
        writer.write()
        self.split_pdf_pages()


    def make_slide(self):
        shutil.copy('slide_template/latexmkrc', self.dirpath / 'slide' / 'latexmkrc')

        with open(self.dirpath / 'slide' / 'main.tex', mode='w') as main:
            with open('slide_template/main.tex') as template:
                s = template.read()
                s = re.sub('PAPERTITLE', self.title, s)
                s = re.sub('PAPERAUTHORS', ', '.join(self.authors), s)
                s = re.sub('PAPERURL', self.url, s)
                main.write(s)

        with open(self.dirpath / 'slide' / 'abs.tex', mode='w') as abstract:
            with open('slide_template/abs.tex') as template:
                s = template.read()
                display(self.abstract)
                s = re.sub('ABSTRACT_TEXT', self.abstract, s)
                abstract.write(s)


        if os.path.isfile(self.dirpath / 'slide' / 'body.tex'): os.remove(self.dirpath / 'slide' / 'body.tex')
        with open(self.dirpath / 'slide' / 'body.tex', mode='a') as body:
            figures = os.listdir(self.figure_path)
            figures.sort()
            for i, figure in enumerate(figures):
                with open('slide_template/body.tex') as template:
                    s = template.read()
                    s = re.sub('FIGURENUMBER', f'{i+1}', s)
                    s = re.sub('FIGUREPATH', 'figures/'+figure, s)
                    body.write(s)


def make_summary(arxiv_id):
    arxiv = readarxiv(arxiv_id)
    arxiv.get_paper()
    arxiv.get_figures()
    arxiv.make_slide()
    return arxiv