#!/usr/bin/env python3
from collections import defaultdict

year = 2018
semester = 3

DAYS = ('M', 'T', 'W', 'Th', 'F')

STYLE = '''
<style>
/*************************************
*    === CSS For HTML Table ===
*************************************/
table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
    table-layout: fixed;
    white-space: nowrap;
}

/* -- Colors for Headers and Data Borders -- */
table th, table td{
    border: 1px solid black;
}

/* -- Make sure the width of the cols is correct -- */
table td {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 80px;
}

/* -- Handles the color-swapping on adjacent columns -- */
.day col:nth-child(odd){
    background: lightgray;
}
.day col:nth-child(even){
    background: gray;
}
</style>
'''

def _start_and_duration(timestr):
    '''Parse start hour and duration from a time span string

    Strings look like "9:00AM - 10:15".
    This function does some very simplistic rounding to the next half-hour.

    Returns (start_hour, duration) where start_hour is the hour in 24-hour
    format and duration is the number of half-hours to the end.

    TODO: it might help to add doctests to this.
    '''

    # parsing string
    start_time, end_time = timestr.split(' - ')

    start_hour, start_minute = start_time.split(':')
    end_hour, end_minute = end_time.split(':')

    start_period = start_minute[-2:]
    start_minute = start_minute[:-2]
    start_hour = int(start_hour)
    start_minute = int(start_minute)

    end_hour = int(end_hour)
    end_minute = int(end_minute)

    # convert to 24-hour
    if start_period == 'PM' and start_hour != 12:
        start_hour += 12
    if end_hour < start_hour:
        end_hour += 12

    # simple half-hour rounding
    if end_minute > 30:
        end_hour += 1
    else:
        end_hour += 0.5

    if start_minute != 0:
        start_hour += 0.5

    # duration in half-hours
    duration = int((end_hour - start_hour) * 2)
    return start_hour, duration

def extract_table_data(courses):
    # {instructor: {day: {start_hour: {label: room, span: duration}}}}
    instructors = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: {'label': '', 'span': 1})))
    # {room: {day: {start_hour: {label: instructor, span: duration}}}}
    rooms = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: {'label': '', 'span': 1})))

    for course in courses:
        course_id = course.get('course_id')
        for ticket in course.get('tickets', []):
            instructor = ticket['instructor']
            for session in ('lecture', 'lab'):
                room = ticket[session]['room']
                days = ticket[session]['day']
                time = ticket[session]['time']
                start, duration = _start_and_duration(time)
                start = int(start*2) # columns are half-hours, not hours
                room_cell = { 'label': instructor, 'span': duration }
                instructor_cell = { 'label': course_id, 'span': duration }
                rooms[room][days][start] = room_cell
                instructors[instructor][days][start] = instructor_cell
                for i in range(1, duration):
                    rooms[room][days][start+i] = None
                    instructors[instructor][days][start+i] = None
                for day in days.split():
                    print(course['course_id'], instructor, session, day, start/2, room)
                    rooms[room][day][start] = room_cell
                    instructors[instructor][day][start] = instructor_cell
                    # insert Nones so that the HTML generator doesn't add extra <td>s
                    for i in range(1, duration):
                        rooms[room][day][start+i] = None
                        instructors[instructor][day][start+i] = None

    return rooms, instructors

def convert_to_table(table_data, days=DAYS):
    rows = []
    table = {
            'rows': rows,
            'day_start': {day: 48 for day in days},
            'day_end': {day: 0 for day in days},
            }

    # find start time and end time of each day
    for head in table_data.keys():
        for day in days:
            if day in table_data[head]:
                day_table = table_data[head][day]
                for time in day_table.keys():
                    slot = day_table[time]
                    if time < table['day_start'][day]:
                        table['day_start'][day] = time
                    if slot and time + slot['span'] > table['day_end'][day]:
                        table['day_end'][day] = time + slot['span']

    # fill in cells for each day
    for head in sorted(table_data.keys()):
        cells = []
        row = {'heading': head, 'cells': cells}
        rows.append(row)

        for day in days:
            day_table = table_data[head][day]
            for time in range(table['day_start'][day], table['day_end'][day]):
                slot = day_table[time]
                if slot:
                    cells.append(slot)

    return table


def generate_html(table, days=DAYS):
    # colgroups are used to apply column-wise CSS styles
    colgroups = [
            '<colgroup><col></colgroup>',
    ]
    for day in days:
        cols = '<col/>' * (table['day_end'][day] - table['day_start'][day])
        colgroups.append('<colgroup class="{} day">{}</colgroup>'.format(
            day, cols))

    headers = [
            '<tr><td></td>',
    ]
    # header for each day
    for day in days:
        cols = table['day_end'][day] - table['day_start'][day]
        headers.append('<th colspan="{}">{}</th>'.format(cols, day))
    headers.append('</tr>')
    headers.append('<tr><td></td>')

    # hours in each day
    for day in days:
        cols = table['day_end'][day] - table['day_start'][day]
        cols //= 2
        for col in range(cols):
            col += table['day_start'][day] // 2
            headers.append('<th colspan="2">{}</th>'.format(col))
    headers.append('</tr>')

    rows = []
    for row in table['rows']:
        labels = []
        for cell in row['cells']:
            labels.append('<td colspan="{}">{}</td>'.format(
                 cell['span'],
                 cell['label']))
        rows.append('<tr><th>{}</th>{}</tr>'.format(
                row['heading'],
                ''.join(labels)))

    html = '''
    <table>
    {colgroups}
    {headers}
    {rows}
    </table>
    '''.format(colgroups=''.join(colgroups),
            headers=''.join(headers),
            rows=''.join(rows))
    return html

if __name__ == '__main__':
    import json

    cFileName = 'courses{year}-{semester}.json'
    with open(cFileName.format(year=year, semester=semester), 'r') as file:
        courses = json.load(file)

    rooms, instructors = extract_table_data(courses)
    days = ('M W', 'T Th', 'F')
    room_table = convert_to_table(rooms, days)
    instructor_table = convert_to_table(instructors, days)

    html = STYLE
    html += generate_html(room_table, days)
    html += '<br><br>'
    html += generate_html(instructor_table, days)
    htmlFileName = 'courses{year}-{semester}.html'
    with open(htmlFileName.format(year=year, semester=semester), 'w') as file:
        file.write(html)

