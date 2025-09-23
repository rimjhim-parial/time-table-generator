import itertools
import polars as pl
from .model import Model
from collections import defaultdict


class Solver:
    def __init__(self, model: Model):
        self.model = model
        self.days = model.slots["days"]["day"].to_list()
        self.times = model.slots["times"]["time"].to_list()
        self.breaks_raw = model.slots["breaks"].to_dicts()
        self.invalid_start_times = self._compute_invalid_start_times()
        self.max_consec = model.constraints.get("maximum_consecutive_classes", 2)

        self.rooms = model.rooms
        self.teachers = model.teachers
        self.subjects = model.subjects
        self.groups = model.groups

        self.room_types = {r["id"]: r["type"] for r in self.rooms.to_dicts()}
        self.lab_for = {
            r["id"]: set(r.get("for", []))
            for r in self.rooms.to_dicts()
            if r["type"] == "lab"
        }

        self.teacher_subjects = {
            t["id"]: set(t["subjects"]) for t in self.teachers.to_dicts()
        }
        self.subject_type = {s["id"]: s["type"] for s in self.subjects.to_dicts()}

        self.subject_names = {s["id"]: s["name"] for s in self.subjects.to_dicts()}
        self.teacher_names = {t["id"]: t["name"] for t in self.teachers.to_dicts()}

        self.group_subjects = {}
        for g in self.groups.to_dicts():
            group_id = g["id"]
            subjects = g.get("subjects", [])
            self.group_subjects[group_id] = set(subjects)

    def _compute_invalid_start_times(self):
        invalid = defaultdict(set)
        for brk in self.breaks_raw:
            days = self.days if brk["day"] == "*" else [brk["day"]]
            for d in days:
                invalid[d].add(brk["time"])
        return invalid

    def _valid_room_for_subject(self, room_id, subject_id):
        rtype = self.room_types[room_id]
        stype = self.subject_type[subject_id]
        if rtype == "lecture" and stype == "lecture":
            return True
        if (
            rtype == "lab"
            and stype == "lab"
            and subject_id in self.lab_for.get(room_id, set())
        ):
            return True
        return False

    def _teacher_available(self, teacher_id, day, time, schedule):
        return all(
            not (c["teacher"] == teacher_id and c["day"] == day and c["time"] == time)
            for c in schedule
        )

    def _room_available(self, room_id, day, time, schedule):
        return all(
            not (c["room"] == room_id and c["day"] == day and c["time"] == time)
            for c in schedule
        )

    def _group_available(self, group_id, day, time, schedule):
        """Check if a specific group is available at the given time"""
        return all(
            not (group_id in c["groups"] and c["day"] == day and c["time"] == time)
            for c in schedule
        )

    def _no_break(self, day, time):
        return time not in self.invalid_start_times.get(day, set())

    def _max_consecutive_ok(self, teacher_id, day, time, schedule):
        day_classes = [
            c for c in schedule if c["teacher"] == teacher_id and c["day"] == day
        ]
        times = sorted(
            self.times.index(t) for t in [c["time"] for c in day_classes] + [time]
        )
        max_cons = 1
        current_cons = 1
        for i in range(1, len(times)):
            if times[i] == times[i - 1] + 1:
                current_cons += 1
                max_cons = max(max_cons, current_cons)
            else:
                current_cons = 1
        return max_cons <= self.max_consec

    def solve(self) -> pl.DataFrame:
        schedule = []

        scheduling_tasks = []
        for group_dict in self.groups.to_dicts():
            group_id = group_dict["id"]
            for subject_id in group_dict.get("subjects", []):
                scheduling_tasks.append((subject_id, group_id))

        for subject_id, group_id in scheduling_tasks:
            available_teachers = [
                t
                for t in self.teachers.to_dicts()
                if subject_id in self.teacher_subjects[t["id"]]
            ]

            assigned = False
            for teacher in available_teachers:
                teacher_id = teacher["id"]
                for day, time in itertools.product(self.days, self.times):
                    if not self._no_break(day, time):
                        continue

                    if not self._teacher_available(teacher_id, day, time, schedule):
                        continue
                    if not self._group_available(group_id, day, time, schedule):
                        continue
                    if not self._max_consecutive_ok(teacher_id, day, time, schedule):
                        continue

                    for room in self.rooms.to_dicts():
                        room_id = room["id"]
                        if not self._valid_room_for_subject(room_id, subject_id):
                            continue
                        if not self._room_available(room_id, day, time, schedule):
                            continue

                        schedule.append(
                            {
                                "subject": subject_id,
                                "subject_name": self.subject_names[subject_id],
                                "teacher": teacher_id,
                                "teacher_name": self.teacher_names[teacher_id],
                                "room": room_id,
                                "day": day,
                                "time": time,
                                "groups": [group_id],
                            }
                        )
                        assigned = True
                        break
                    if assigned:
                        break
                if assigned:
                    break

        rows = []
        for c in schedule:
            rows.append(
                {
                    "Day": c["day"],
                    "Time": c["time"],
                    "Subject": c["subject_name"],
                    "Teacher": c["teacher_name"],
                    "Room": c["room"],
                    "Groups": ", ".join(c["groups"]),
                }
            )

        if rows:
            df = pl.DataFrame(rows)
            df = df.sort(["Day", "Time"])
            return df
        else:
            return pl.DataFrame(
                {
                    "Day": [],
                    "Time": [],
                    "Subject": [],
                    "Teacher": [],
                    "Room": [],
                    "Groups": [],
                }
            )
