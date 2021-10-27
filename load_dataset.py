import csv
from datetime import datetime, timedelta
import math as m
import copy
from functools import cmp_to_key


def load_tsv_table(filename):

    tsv = open(filename)
    items = []

    headers = []

    reader = csv.reader(tsv, delimiter='\t', quotechar='"')
    for row in reader:

        # if the headers have not been read yet then read them
        if len(headers) == 0:
            for cell in row:
                if cell[0] == '#':
                    cell = cell[1:]
                headers.append(cell)
            # print("found headers : %s" % str(headers))
            continue

        # skip comments
        if row[0][0] == '#':
            continue

        # read row
        item = {}
        for idx in range(min(len(headers), len(row))):
            item[headers[idx]] = row[idx]
        # print("Adding item:\n%s" % str(item))
        items.append(item)

    tsv.close()
    return items


class DuplicatedMissionNameException(Exception):
    pass


class HSFDataset:

    def __init__(self, trips_filename, missions_filename):

        self.trips = self.load_trips(trips_filename)
        self.missions = self.load_missions(missions_filename)

        astronauts_names = list(set(map(lambda trip: trip['Name'], self.trips)))
        self.astronauts = {}
        for name in astronauts_names:
            nationality = None
            for trip in self.trips:
                if trip['Name'] == name:
                    nationality = trip['Nationality']
                    break
            assert nationality is not None
            self.astronauts[name] = {'Nationality': nationality}
            self.astronauts[name].update(self.split_name(name))
        self.add_astronaut_first_launch_times()

        self.validate_dataset()

    @staticmethod
    def load_trips(filename):
        trips = []
        csv_file = open(filename)
        reader = csv.reader(csv_file, delimiter=',', quotechar='"')
        skip = 2
        for row in reader:
            if skip > 0:
                skip -= 1
                continue

            entry = {'Name': row[0].strip(),
                     'Nationality': row[1].strip(),
                     'LaunchMission': row[2].strip(),
                     'LandingMission': row[3].strip()}
            """print("%s (%s) [%s -> %s]" % (
                entry['Name'],
                entry['Nationality'],
                entry['LaunchMission'],
                entry['LandingMission']
            ))"""
            trips.append(entry)
        return trips

    @staticmethod
    def load_missions(filename):
        missions = {}
        csv_file = open(filename)
        reader = csv.reader(csv_file, delimiter=',', quotechar='"')
        skip = 1
        for row in reader:
            if skip > 0:
                skip -= 1
                continue

            launch_time = datetime.strptime(row[3].strip(), '%d/%m/%Y %H:%M:%S')
            if row[4].strip() == "<now>":
                landing_time = datetime.now()
            elif row[4].strip() == "":
                landing_time = None
            else:
                landing_time = datetime.strptime(row[4].strip(), '%d/%m/%Y %H:%M:%S')

            key = row[0]

            # check mission name is unique
            if key in missions.keys():
                raise DuplicatedMissionNameException("Mission name [%s] already exists" % key)

            entry = {'Organisation': row[1].strip(),
                     'LaunchSite': row[2].strip(),
                     'LaunchTime': launch_time,
                     'LandingTime': landing_time}
            duration = None
            try:
                duration = entry['LandingTime'] - entry['LaunchTime']
            except TypeError:
                pass
            entry['Duration'] = duration

            """print("%s (%s) [%s -> %s] duration %s" % (
                key,
                entry['Organisation'],
                entry['LaunchTime'],
                entry['LandingTime'],
                duration
            ))"""
            missions[key] = entry
        return missions

    def validate_dataset(self):

        # check all missions keys in the trips table exist
        for trip in self.trips:
            if trip["LaunchMission"] not in self.missions.keys():
                print("Launch Mission \"%s\" missing from missions table" % trip["LaunchMission"])
            if trip["LandingMission"] not in self.missions.keys():
                print("Landing Mission \"%s\" missing from missions table" % trip["LandingMission"])

        # check all missions are referenced at least once
        mission_ref_counts = dict(zip(self.missions.keys(), [0] * len(self.missions)))
        for trip in self.trips:
            if trip["LaunchMission"] in self.missions.keys():
                mission_ref_counts[trip["LaunchMission"]] += 1
            if trip["LandingMission"] in self.missions.keys():
                mission_ref_counts[trip["LandingMission"]] += 1
        for mission, count in mission_ref_counts.items():
            if count == 0:
                print("Mission \"%s\" not referenced by any trips" % mission)

        # check all landings occurred after launches
        for trip in self.trips:
            if trip["LaunchMission"] in self.missions.keys() and trip["LandingMission"] in self.missions.keys():
                if self.missions[trip["LandingMission"]]["LandingTime"] is not None:
                    if (self.missions[trip["LaunchMission"]]["LaunchTime"] >
                            self.missions[trip["LandingMission"]]["LandingTime"]):
                        print("%s trip on %s->%s landed before it launched!" % (
                            trip["Name"],
                            trip["LaunchMission"],
                            trip["LandingMission"]
                        ))

    @staticmethod
    def split_name(name):
        words = name.split(" ")
        parts = {'NameSuffix':''}
        if words[-1] == "Jr":
            parts['NameSuffix'] = "Jr"
            parts['FirstNames'] = " ".join(words[:-2])
            parts['LastNames'] = " ".join(words[-2:])
        else:
            parts['FirstNames'] = " ".join(words[:-1])
            parts['LastNames'] = words[-1]
        return parts

    def get_astronaut_names(self):
        """
        Gets a list of unique Astronaut names in this Dataset
        :return: List of names in alphabetical order
        """
        # names = map(lambda x:x["Name"], self.trips)
        names = list(set(self.astronauts.keys()))

        def sort_key(x):
            words = x.split(" ")
            if words[-1] == "Jr":
                first_names = " ".join(words[:-2])
                last_name = " ".join(words[-2:])
            else:
                first_names = " ".join(words[:-1])
                last_name = words[-1]
            return last_name + " " + first_names

        return sorted(names, key=sort_key)

    def get_astronaut_trips(self, astronaut_name):

        trips = filter(lambda x:x["Name"] == astronaut_name, self.trips)

        def trip_sort_key(x):
            return self.missions[x["LaunchMission"]]["LaunchTime"]

        return sorted(trips, key=trip_sort_key)

    def get_astronaut_first_launch_time(self, astronaut_name):
        trips = self.get_astronaut_trips(astronaut_name)
        first_launch_time = self.missions[trips[0]["LaunchMission"]]["LaunchTime"]
        return first_launch_time

    def add_astronaut_first_launch_times(self):
        for name in self.astronauts.keys():
            first_launch_time = self.get_astronaut_first_launch_time(name)
            self.astronauts[name]['FirstLaunchTime'] = first_launch_time

    def get_trip_duration(self, trip):
        launch_mission = self.missions[trip["LaunchMission"]]
        landing_mission = self.missions[trip["LandingMission"]]
        if launch_mission["LaunchTime"] is not None and landing_mission["LandingTime"] is not None:
            return landing_mission["LandingTime"] - launch_mission["LaunchTime"]
        else:
            return None


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


def total_time_on_orbit(dataset):

    total_time = 0
    for trip in dataset.trips:
        if trip["LandingMission"] in dataset.missions.keys():
            launch_time = dataset.missions[trip["LaunchMission"]]["LaunchTime"]
            landing_time = dataset.missions[trip["LandingMission"]]["LandingTime"]
            if launch_time is not None and landing_time is not None:
                total_time += (landing_time - launch_time).total_seconds() / (24 * 60 * 60)
    return total_time


def print_trips_per_programme(dataset):

    programmes = {}
    for trip in dataset.trips:
        mission_name = trip["LaunchMission"]
        # remove number from mission name to get programme name
        programme_name = ''.join([i for i in mission_name if not i.isdigit()])
        if programme_name in programmes.keys():
            programmes[programme_name] += 1
        else:
            programmes[programme_name] = 1

    for programme, count in programmes.items():
        print("%s - %d trips" % (programme, count))


def print_longest_n_trips(dataset, n):
    trips = copy.copy(dataset.trips)
    for trip in trips:
        trip['Duration'] = dataset.get_trip_duration(trip)

    def sort_fn(x, y):
        x_duration = x['Duration']
        if x_duration is None:
            x_duration = timedelta()
        y_duration = y['Duration']
        if y_duration is None:
            y_duration = timedelta()
        return float(y_duration.total_seconds() - x_duration.total_seconds())

    trips = sorted(trips, key=cmp_to_key(sort_fn))

    for trip in trips[:n]:
        print(trip)


def get_flown_astro_count_to_date(dataset, upto_date):
    astronauts = dataset.get_astronaut_names()
    count = 0
    for astronaut in astronauts:
        if dataset.get_astronaut_first_launch_time(astronaut) <= upto_date:
            count += 1
    return count


def read_names_check():
    filename = "names_check.txt"
    names_file = open(filename)

    names = []
    in_parenthesis = False

    current_str = ""

    while True:
        c = names_file.read(1)
        if not c:
            break

        if not in_parenthesis:
            if c == "<":
                if current_str.strip() != "" and len(current_str.strip()) > 1:
                    parts = current_str.strip().split(".")
                    last_name = parts[-1]
                    initials = ".".join(parts[:-1])
                    names.append({'Original': current_str.strip() ,'Initials': initials, 'LastName': last_name})
                    print(names[-1])
                current_str = ""
                in_parenthesis = True
            else:
                current_str += c
                if current_str == "&nbsp;":
                    current_str = ""

        if in_parenthesis:
            if c == ">":
                in_parenthesis = False

    names_file.close()

    print("%d names found in test set" % len(names))

    return names


def compare_with_planet_4589_data():
    missions = load_tsv_table("planet4589_data/missions.tsv")
    trips = load_tsv_table("planet4589_data/rides.tsv")

    # get orbital astro first launch time
    astro_first_trips = {}
    for trip in trips:
        astro_id = trip["ID"]
        mission_label = trip["Mission"].strip()
        mission_tag = trip["RoleCode"].split("/")[0]

        print("Searching for %s" % mission_tag)

        orbital_mission = False
        launch_date = None

        for mission in missions:
            # print("Comparing with [%s] and <%s>" % (mission["Ship"].strip(), mission["OrbID"][:3]))
            if mission["HSFTAG"].strip() == mission_tag and mission["OrbID"][:3].lower() == "orb":
                launch_date_str = mission["LDate"]
                try:
                    launch_date = datetime.strptime(launch_date_str.strip(), '%Y %b %d %H%M:%S')
                except ValueError as e:
                    pass
                try:
                    launch_date = datetime.strptime(launch_date_str.strip(), '%Y %b %d %H%M')
                except ValueError as e:
                    pass
                try:
                    launch_date = datetime.strptime(launch_date_str.strip(), '%Y %b %d')
                except ValueError as e:
                    pass
                if launch_date is not None:
                    orbital_mission = True
                    break

        if orbital_mission:
            if astro_id not in astro_first_trips.keys() or launch_date < astro_first_trips[astro_id]["FirstTrip"]:
                astro_first_trips[astro_id] = {"FirstTrip": launch_date, "Mission": mission_label}
                print("Found first trip")
            else:
                print("Found veteran trip")

    print("Found %d orbital first trips" % len(astro_first_trips))
    return astro_first_trips


def main():

    human_spaceflight_dataset = HSFDataset(trips_filename="trips_to_space.csv",
                                           missions_filename="missions.csv")

    days_in_orbit = total_time_on_orbit(human_spaceflight_dataset)
    print("Total time spent in orbit: %f days (%f years)" % (days_in_orbit, days_in_orbit / 365))

    # print_trips_per_programme(human_spaceflight_dataset)

    """astronauts = human_spaceflight_dataset.get_astronaut_names()
    print("Found %d astronaut names" % len(astronauts))
    for astronaut in astronauts:
        trips = human_spaceflight_dataset.get_astronaut_trips(astronaut)
        time_in_space = timedelta()
        for trip in trips:
            duration = human_spaceflight_dataset.get_trip_duration(trip)
            if duration is not None:
                time_in_space += duration
        print("[%s] %d trips [%s in space]\n-------------------" % (astronaut, len(trips), time_in_space))
        for trip in trips:
            print(trip)
        print("-" * 30)"""

    print("Longest 10 trips in space")
    print_longest_n_trips(human_spaceflight_dataset, 10)

    upto_date = datetime.now()
    print("Up to [%s] %d astronauts have flown to orbit" % (
        upto_date,
        get_flown_astro_count_to_date(human_spaceflight_dataset, upto_date)
    ))

    p4589_first_trips = compare_with_planet_4589_data()

    """print("Orbital Astronaut names in alphabetical order:")
    for astro_name in human_spaceflight_dataset.get_astronaut_names():
        # if human_spaceflight_dataset.astronauts[astro_name]['Nationality'] == "Chinese":
        first_launch_time = human_spaceflight_dataset.astronauts[astro_name]['FirstLaunchTime']
        if first_launch_time <= datetime.now():
            print(astro_name)"""

    start_date = datetime(1961, 1, 1)  # The year human spaceflight began!
    current_date = start_date
    step = timedelta(30)  # 1 week
    print("Date, Astro Count")
    diffs_found = 0
    while current_date < datetime.now():
        astro_count = 0  # get_flown_astro_count_to_date(human_spaceflight_dataset, current_date)
        for name, info in human_spaceflight_dataset.astronauts.items():
            if info['FirstLaunchTime'] < current_date:
                astro_count += 1

        check_count = 0
        for id, info in p4589_first_trips.items():
            if info["FirstTrip"] < current_date:
                check_count += 1

        if astro_count != check_count:
            diffs_found += 1

        print("%s, HSD %d, P4589 %d | %d" % (current_date, astro_count, check_count, (astro_count - check_count) * 1000))
        current_date += step

    print("%d difference found between p4589 data and my data" % diffs_found)

    """check_names = read_names_check()

    for astro_name in human_spaceflight_dataset.get_astronaut_names():
        last_names = human_spaceflight_dataset.astronauts[astro_name]['LastNames']
        first_names = human_spaceflight_dataset.astronauts[astro_name]['FirstNames']

        found = False
        found_str = ""
        for check_name in check_names:
            if check_name['LastName'].lower() == last_names.lower():
                found_str + "Found %s\n" % str(check_name)
                found = True

        if not found:
            print("Searching for [%s - %s] no matches found" % (last_names, first_names))"""


if __name__ == "__main__":
    main()
