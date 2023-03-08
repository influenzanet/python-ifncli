from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import calendar

days = {
    'monday': calendar.MONDAY,
    'mon': calendar.MONDAY,
    'tuesday': calendar.TUESDAY,
    'tue': calendar.TUESDAY,
    'wednesday': calendar.WEDNESDAY,
    'wed': calendar.WEDNESDAY,
    'thursday': calendar.THURSDAY,
    'thu': calendar.THURSDAY,
    'friday': calendar.FRIDAY,
    'fri': calendar.FRIDAY,
    'saturday': calendar.SATURDAY,
    'sat': calendar.SATURDAY,
    'sunday':calendar.SUNDAY,
    'sun':calendar.SUNDAY,
}

def parse_relative_time(time, now):
    """
        Apply relative rule, each component shift the given 'now' time with the given value
        
    """
    if 'hour' in time:
        r = relativedelta(hours=int(time['hour']))
        now = now + r
    if 'min' in time:
        r = relativedelta(minutes=int(time['min']))
        now = now + r
    if 'day' in time:
        r = relativedelta(days=int(time['day']))
        now = now + r
    if 'weekday' in time:
        w = time['weekday']
        if not w in days:
           raise Exception("weekday must be a string among " + ",".join(days.keys())) 
        weekday = days[w]
        r = relativedelta(weekday=+weekday)
        now = now + r
    return now

def parse_fixed_time(time, now):
    """
        Parse rule for fixed time, apply the given value for the passed time
    """
    if 'hour' in time:
        now = now.replace(hour=int(time['hour']))
    if 'min' in time:
        now = now.replace(minute=int(time['min']))
    return now

def parse_time_rules(rules):
    """
        Parse a list of time rules, and apply it, starting with initial time = current time (normalized with seconds=0)
        each time rule can be:
            - a iso time string YYYY-MM-DD HH:mm:SS
            - a dictionnary 
                - fixed hour or min (fix the given value)
                - relative with hour, min, day, weekday (apply the +x value for the previous rule time, rule[0] = current time)

        For example, for next sunday at 14:00 (relative time for next sunday, and fixed time for hour & min)
            - relative: true
              weekday: 'sunday'
            - hour: 14
              min: 0

    """
    now = datetime.now().replace(second=0, microsecond=0)
   
    if not isinstance(rules, list):
        rules = [rules]
    
    for rule in rules:
        if isinstance(rule, str):
            now = datetime.strptime(rule, "%Y-%m-%d-%H:%M:%S")
        elif isinstance(rule, dict):
            if 'relative' in rule and rule['relative']:
                now = parse_relative_time(rule, now)
            else:
                now = parse_fixed_time(rule, now)
        else:
            raise Exception("Unable to handle this rule (must be dict or str)")
    return now
