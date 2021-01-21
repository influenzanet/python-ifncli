from .models import Expression, TranslatableList, Translatable, Timestamp
from .survey import survey_parser
from .expression import render_expression
from jinja2 import Template, FileSystemLoader, Environment
import os

known_styles = {
  'item': 'card',
  'translate-list': 'list-unstyled',
  'trans-code': 'badge badge-light',
  'components': 'card',
  'item-version': 'badge badge-success',
  'role': 'badge badge-warning',
}

def styles(name):
    if name in known_styles:
        return known_styles[name] + ' '+ name
    return name

def survey_to_html(survey, context):

    survey = survey_parser(survey)

    path = os.path.dirname(os.path.abspath(__file__))

    env = Environment(
      loader=FileSystemLoader(path + '/templates/html'),
        autoescape='html',
    )
    env.globals['language'] = context.get_language()
    env.globals['context'] = context
    env.globals['styles'] = styles
    
    template = env.get_template('survey.html')
    
    with open(path + '/templates/html/survey.css') as f:
        theme = f.read()

    ctx = {
        'survey': survey,
        'theme_css': theme
    }
    return template.render(ctx)


