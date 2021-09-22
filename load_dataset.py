import csv
from datetime import datetime
import math as m

def parse_duration_cells(days_str, time_str):
    hh, mm = time_str.split(':')
    h_int = int(hh)
    m_int = int(mm)
    days = int(days_str)
    duration = days + (h_int / 24.0) + (m_int / (24.0 * 60.0))
    return duration


def load_people_table(filename):
    people = []
    csv_file = open(filename)
    reader = csv.reader(csv_file, delimiter=',', quotechar='"')
    skip = 2
    for row in reader:
        if skip > 0:
            skip -= 1
            continue

        duration = parse_duration_cells(row[5], row[6])
        launch_time = datetime.strptime(row[3], '%d/%m/%Y %H:%M')
        landing_time = datetime.strptime(row[4], '%d/%m/%Y %H:%M')

        entry = {'Name': row[0],
                 'Nationality': row[1],
                 'Mission': row[2],
                 'LaunchTime': launch_time,
                 'LandingTime': landing_time,
                 'Duration': duration}
        print("%s (%s) %s, [%s -> %s] duration %f days" % (
            entry['Name'],
            entry['Nationality'],
            entry['Mission'],
            launch_time,
            landing_time,
            duration
        ))
        people.append(entry)
    return people


def duration_to_str(duration):
    years = m.floor(duration / 365)
    days = m.floor(duration - (years * 365))
    hours = m.floor((duration - (years * 265) - days) * 24)
    return "%d years %d days %d hours" % (years, days, hours)


def print_person_stats(people_table):
    people = {}
    total_duration = 0.0

    for person in people_table:
        total_duration += person['Duration']
        if person['Name'] in people.keys():
            people[person['Name']]['Flights'] += 1
            people[person['Name']]['Missions'] += ", " + person['Mission']
            people[person['Name']]['Time in Space'] += person['Duration']
        else:
            people[person['Name']] = {'Nationality': person['Nationality'],
                                      'Flights': 1,
                                      'Missions': person['Mission'],
                                      'Time in Space': person['Duration']}

    names = sorted(list(people.keys()))

    print("\n%d people have been to space for a total of %s (%f days)\n" % (
        len(people),
        duration_to_str(total_duration),
        total_duration
    ))

    for name in names:
        print("%s (%s) flights %d, missions [%s] time in space %f days" % (
            name,
            people[name]['Nationality'],
            people[name]['Flights'],
            people[name]['Missions'],
            people[name]['Time in Space']
        ))


def main():
    people_table = load_people_table("people_in_space.csv")

    print_person_stats(people_table)


if __name__ == "__main__":
    main()
