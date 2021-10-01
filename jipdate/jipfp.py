#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from argparse import ArgumentParser

import logging as log
import os
import re
import sys
import unicodedata
import yaml

# Local files
from jipdate import cfg
from jipdate import jiralogin

################################################################################
# Class node
################################################################################
class Node():
    """A node representing an issue in Jira"""
    def __init__(self, key, summary, issuetype):
        """Return a node containing the must have feature to be represented in a
        tree."""
        self.key = key
        self.summary = summary
        # Take care of some characters not supported in xml
        self.summary = self.summary.replace("\"", "'")
        self.summary = self.summary.replace("&", "and")
        self.issuetype = issuetype
        self.assignee = None
        self.sponsors = []
        self.description = None
        self.parent = None
        self.childrens = []
        self.state = None
        self.color = None
        self.base_url = None

        self._indent = 0
        self._sortval = 3

    def __str__(self):
        s =  "%s%s: %s [%s]\n"              % (" " * self._indent, self.key, self.summary, self.issuetype)
        s += "%s     |   sponsors:    %s\n" % (" " * self._indent, ", ".join(self.sponsors))
        s += "%s     |   assignee:    %s\n" % (" " * self._indent, self.assignee)
        s += "%s     |   description: %s\n" % (" " * self._indent, self.description)
        s += "%s     |   parent:      %s\n" % (" " * self._indent, self.parent)
        s += "%s     |   state:       %s\n" % (" " * self._indent, self.state)
        s += "%s     |   url:         %s\n" % (" " * self._indent, self.get_url())
        s += "%s     |-> color:       %s\n" % (" " * self._indent, self.get_color())
        return s

    def __lt__(self, other):
        return self._sortval < other._sortval

    def _short_type(self):
        st = "I"
        if self.issuetype == "Epic":
            st = "E"
        elif self.issuetype == "Story":
            st = "S"
        return st

    def get_key(self):
        return self.key

    def add_assignee(self, assignee):
        self.assignee = assignee

    def get_assignee(self):
        return self.assignee

    def add_sponsor(self, sponsor):
        self.sponsors.append(sponsor)

    def get_sponsor(self, sponsor):
        return self.sponsors

    def add_description(self, description):
        self.description = description

    def get_description(self, description):
        #try:
        #    f.write("<richcontent TYPE=\"DETAILS\" HIDDEN=\"true\"\n>")
        #    f.write("<html>\n<head>\n</head>\n<body>\n<p>\n")
        #    f.write(issue.fields.description)
        #except UnicodeEncodeError:
        #    vprint("UnicodeEncodeError in description in %s" % str(issue))
        #    f.write("Unicode error in description, please go to Jira\n")
        #f.write("\n</p>\n</body>\n</html>\n</richcontent>\n")
        return self.description

    def add_parent(self, key):
        self.parent = key

    def get_parent(self):
        return self.key

    def add_child(self, node):
        node.add_parent(self.key)
        self.childrens.append(node)

    def set_state(self, state):
        self.state = state

        if self.state in ["In Progress"]:
            self._sortval = int(1)
        elif self.state in ["To Do", "Blocked"]:
            self._sortval = int(2)
        else:
            self._sortval = int(3)

    def get_state(self):
        return self.state

    def set_color(self, color):
        self.color = color

    def get_color(self):
        if self.color is not None:
            return self.color

        color = "#990000" # Red
        if self.state == "In Progress":
            color = "#009900" # Green
        elif self.state in ["Blocked", "To Do"]:
            color = "#ff6600" # Orange
        return color

    def set_base_url(self, base_url):
        self.base_url = base_url

    def get_url(self):
        if self.base_url is not None:
            return self.base_url + "/browse/" + self.key
        else:
            return self.base_url

    def gen_tree(self, indent=0):
        self._indent = indent
        print(self)
        for c in self.childrens:
            c.gen_tree(self._indent + 4)

    def to_xml(self, f, indent=0):
        self._indent = indent
        # Main node
        fold = "false"
        if self.issuetype in ["Epic", "Story"]:
            fold = "true"

        if cfg.args.s and self.issuetype == "Epic":
            fold = "false"

        if cfg.args.i and self.issuetype == "Initiative":
            fold = "true"

        xml_start = "%s<node LINK=\"%s\" TEXT=\"%s/%s: %s\" FOLDED=\"%s\" COLOR=\"%s\">\n" % \
                (" " * self._indent,
                 self.get_url(),
                 self._short_type(),
                 self.key,
                 self.summary,
                 fold,
                 self.get_color())
        f.write(xml_start)

        # Info start
        xml_info_start = "%s<node TEXT=\"info\" FOLDED=\"true\" COLOR=\"#000000\">\n" % \
                (" " * (self._indent + 4))
        f.write(xml_info_start)

        # Assignee, single node
        xml_assignee = "%s<node TEXT=\"Assignee: %s\" FOLDED=\"false\" COLOR=\"#000000\"/>\n" % \
                (" " * (self._indent + 8),
                        self.assignee)
        f.write(xml_assignee)

        # Sponsors
        xml_sponsor_start = "%s<node TEXT=\"Sponsors\" FOLDED=\"false\" COLOR=\"#000000\">\n" % \
                (" " * (self._indent + 8))
        f.write(xml_sponsor_start)

        for s in self.sponsors:
            xml_sponsor = "%s<node TEXT=\"%s\" FOLDED=\"false\" COLOR=\"#000000\"/>\n" % \
                    (" " * (self._indent + 12), s)
            f.write(xml_sponsor)

        # Sponsors end
        xml_sponsor_end = "%s%s" % (" " * (self._indent + 8), "</node>\n")
        f.write(xml_sponsor_end)

        # Info end
        xml_info_end = "%s%s" % (" " * (self._indent + 4), "</node>\n")
        f.write(xml_info_end)

        # Recursive print all childrens
        for c in sorted(self.childrens):
            c.to_xml(f, self._indent + 4)

        # Add the closing element
        xml_end = "%s%s" % (" " * self._indent, "</node>\n")
        f.write(xml_end)

def open_file(filename):
    """
    This will open the user provided file and if there has not been any file
    provided it will create and open a temporary file instead.
    """
    log.debug("filename: %s\n" % filename)
    if filename:
        return open(filename, "w")
    else:
        return tempfile.NamedTemporaryFile(delete=False)

def get_parent_key(jira, issue):
    if hasattr(issue.fields, "customfield_10005"):
        return getattr(issue.fields, "customfield_10005");
    return None

################################################################################
# Argument parser
################################################################################
def get_parser():
    """ Takes care of script argument parsing. """
    parser = ArgumentParser(description='Script used to generate Freeplane mindmap files')

    parser.add_argument('-i', required=False, action="store_true", \
            default=False, \
            help='Show Initiatives only')

    parser.add_argument('-p', '--project', required=False, action="store", \
            default="SWG", \
            help='Project type (SWG, VIRT, KWG etc)')

    parser.add_argument('-s', required=False, action="store_true", \
            default=False, \
            help='Show stories also')

    parser.add_argument('-t', required=False, action="store_true", \
            default=False, \
            help='Use the test server')

    parser.add_argument('-v', required=False, action="store_true", \
            default=False, \
            help='Output some verbose debugging info')

    parser.add_argument('--all', required=False, action="store_true", \
            default=False, \
            help='Load all Jira issues, not just the once marked in progress.')

    parser.add_argument('--desc', required=False, action="store_true", \
            default=False, \
            help='Add description to the issues')

    parser.add_argument('--test', required=False, action="store_true", \
            default=False, \
            help='Run test case and then exit')

    return parser

################################################################################
# General nodes
################################################################################
def root_nodes_start(f, key):
    f.write("<map version=\"freeplane 1.6.0\">\n")
    f.write("<node LINK=\"%s\" TEXT=\"%s\" FOLDED=\"false\" COLOR=\"#000000\" LOCALIZED_STYLE_REF=\"AutomaticLayout.level.root\">\n"
        % (cfg.server + "/projects/" + key, key))

def root_nodes_end(f):
    f.write("</node>\n</map>")

def orphan_node_start(f):
    f.write("<node TEXT=\"Orphans\" POSITION=\"left\" FOLDED=\"false\" COLOR=\"#000000\">\n")

def orphan_node_end(f):
    f.write("</node>\n")

################################################################################
# Test
################################################################################
def test():
    f = open_file("test" + ".mm")
    root_nodes_start(f, "Test")
    n1 = Node("SWG-1", "My issue 1", "Initiative")

    n12 = Node("SWG-12", "My issue 12", "Epic")
    n200 = Node("SWG-200", "My issue 200", "Story")
    n201 = Node("SWG-201", "My issue 201", "Story")
    n12.add_child(n200)
    n12.add_child(n201)

    n13 = Node("SWG-13", "My issue 13", "Epic")
    n13.add_assignee("Joakim")
    n13.set_state("In Progress")

    n14 = Node("SWG-14", "My issue 14", "Epic")
    n202 = Node("SWG-202", "My issue 202", "Story")
    n202.set_state("In Progress")
    n203 = Node("SWG-203", "My issue 203", "Story")
    n203.set_state("Blocked")
    n204 = Node("SWG-204", "My issue 204", "Story")
    n204.set_state("In Progress")
    n205 = Node("SWG-205", "My issue 205", "Story")

    n14.add_child(n202)
    n14.add_child(n203)
    n14.add_child(n204)
    n14.add_child(n205)
    n14.add_assignee("Joakim")
    n14.set_state("To Do")
    n14.set_color("#0000FF")
    n14.add_sponsor("STE")
    n14.add_sponsor("Arm")
    n14.add_sponsor("Hisilicon")
    n14.set_base_url(cfg.server)

    n1.add_child(n12)
    n1.add_child(n13)
    n1.add_child(n14)

    n1.gen_tree()
    n1.to_xml(f)
    root_nodes_end(f)
    f.close()

################################################################################
# Stories
################################################################################
def build_story_node(jira, story_key, d_handled=None, epic_node=None):
    si = jira.issue(story_key)
    if si.fields.status.name in ["Closed", "Resolved"]:
        d_handled[str(si.key)] = [None, si]
        return None

    # To prevent UnicodeEncodeError ignore unicode
    summary = str(si.fields.summary.encode('ascii', 'ignore').decode())
    story = Node(str(si.key), summary, str(si.fields.issuetype))

    try:
        assignee = str(si.fields.assignee.displayName.encode('ascii', 'ignore').decode())
    except AttributeError:
        assignee = str(si.fields.assignee)
    story.add_assignee(assignee)

    story.set_state(str(si.fields.status.name))
    story.set_base_url(cfg.server)

    if epic_node is not None:
        story.add_parent(epic_node.get_key())
        epic_node.add_child(story)
    else:
        # This cateches when people are not using implements/implemented by, but
        # there is atleast an "Epic" link that we can use.
        parent = get_parent_key(jira, si)
        if parent is not None and parent in d_handled:
            parent_node = d_handled[parent][0]
            if parent_node is not None:
                story.add_parent(parent_node)
                parent_node.add_child(story)
            else:
                log.debug("Didn't find any parent")

    print(story)
    d_handled[story.get_key()] = [story, si]
    return story


################################################################################
# Epics
################################################################################
def build_epics_node(jira, epic_key, d_handled=None, initiative_node=None):
    ei = jira.issue(epic_key)

    if ei.fields.status.name in ["Closed", "Resolved"]:
        d_handled[str(ei.key)] = [None, ei]
        return None

    summary = str(ei.fields.summary.encode('ascii', 'ignore').decode())
    epic = Node(str(ei.key), summary, str(ei.fields.issuetype))

    try:
        assignee = str(ei.fields.assignee.displayName.encode('ascii', 'ignore').decode())
    except AttributeError:
        assignee = str(ei.fields.assignee)
    epic.add_assignee(assignee)

    epic.set_state(str(ei.fields.status.name))

    try:
        sponsors = ei.fields.customfield_10101
        if sponsors is not None:
            for s in sponsors:
                epic.add_sponsor(str(s.value))
    except AttributeError:
        epic.add_sponsor("No sponsor")


    epic.set_base_url(cfg.server)

    if initiative_node is not None:
        epic.add_parent(initiative_node.get_key())
        initiative_node.add_child(epic)
    else:
        # This cateches when people are not using implements/implemented by, but
        # there is atleast an "Initiative" link that we can use.
        parent = get_parent_key(jira, ei)
        if parent is not None and parent in d_handled:
            parent_node = d_handled[parent][0]
            if parent_node is not None:
                epic.add_parent(parent_node)
                parent_node.add_child(epic)
            else:
                log.debug("Didn't find any parent")

    d_handled[epic.get_key()] = [epic, ei]

    # Deal with stories
    for link in ei.fields.issuelinks:
        if "inwardIssue" in link.raw:
            story_key = str(link.inwardIssue.key)
            build_story_node(jira, story_key, d_handled, epic)

    print(epic)
    return epic

################################################################################
# Initiatives
################################################################################
def build_initiatives_node(jira, issue, d_handled):
    if issue.fields.status.name in ["Closed", "Resolved"]:
        d_handled[str(issue.key)] = [None, issue]
        return None

    summary = str(issue.fields.summary.encode('ascii', 'ignore').decode())
    initiative = Node(str(issue.key), summary, str(issue.fields.issuetype))

    try:
        assignee = str(issue.fields.assignee.displayName.encode('ascii', 'ignore').decode())
    except AttributeError:
        assignee = str(issue.fields.assignee)
    initiative.add_assignee(assignee)

    initiative.set_state(str(issue.fields.status.name))

    sponsors = None
    if hasattr(issue.fields, "customfield_10101"):
        sponsors = issue.fields.customfield_10101

    if sponsors is not None:
        for s in sponsors:
            initiative.add_sponsor(str(s.value))
    initiative.set_base_url(cfg.server)
    print(initiative)

    d_handled[initiative.get_key()] = [initiative, issue] # Initiative

    # Deal with Epics
    for link in issue.fields.issuelinks:
        if "inwardIssue" in link.raw:
            epic_key = str(link.inwardIssue.key)
            build_epics_node(jira, epic_key, d_handled, initiative)

    return initiative


def build_initiatives_tree(jira, key, d_handled):
    jql = "project=%s AND issuetype in (Initiative)" % (key)
    initiatives = jira.search_issues(jql)

    nodes = []
    for i in initiatives:
        node = build_initiatives_node(jira, i, d_handled)
        if node is not None:
            nodes.append(node)
    return nodes


def build_orphans_tree(jira, key, d_handled):
    jql = "project=%s" % (key)
    all_issues = jira.search_issues(jql)

    orphans_initiatives = []
    orphans_epics = []
    orphans_stories = []
    for i in all_issues:
        if str(i.key) not in d_handled:
            if i.fields.status.name in ["Closed", "Resolved"]:
                continue
            else:
                if i.fields.issuetype.name == "Initiative":
                    orphans_initiatives.append(i)
                elif i.fields.issuetype.name == "Epic":
                    orphans_epics.append(i)
                elif i.fields.issuetype.name == "Story":
                    orphans_stories.append(i)

    # Now we three list of Jira tickets not touched before, let's go over them
    # staring with Initiatives, then Epics and last Stories. By doing so we
    # should get them nicely layed out in the orphan part of the tree.

    nodes = []
    log.debug("Orphan Initiatives ...")
    for i in orphans_initiatives:
        node = build_initiatives_node(jira, i, d_handled)
        nodes.append(node)

    log.debug("Orphan Epics ...")
    for i in orphans_epics:
        node = build_epics_node(jira, str(i.key), d_handled)
        nodes.append(node)

    log.debug("Orphan Stories ...")
    for i in orphans_stories:
        node = build_story_node(jira, str(i.key), d_handled)
        nodes.append(node)

    return nodes

################################################################################
# Config files
################################################################################
def get_config_file():
    """ Returns the location for the config file (including the path). """
    for d in cfg.config_locations:
        for f in [cfg.config_filename, cfg.config_legacy_filename]:
            checked_file = d + "/" + f
            if os.path.isfile(checked_file):
                return d + "/" + f

def initiate_config():
    """ Reads the config file (yaml format) and returns the sets the global
    instance.
    """
    cfg.config_file = get_config_file()
    if not os.path.isfile(cfg.config_file):
        create_default_config()

    log.debug("Using config file: %s" % cfg.config_file)
    with open(cfg.config_file, 'r') as yml:
        cfg.yml_config = yaml.load(yml)

################################################################################
# Main function
################################################################################
def main():
    argv = sys.argv
    parser = get_parser()

    # The parser arguments (cfg.args) are accessible everywhere after this call.
    cfg.args = parser.parse_args()

    # This initiates the global yml configuration instance so it will be
    # accessible everywhere after this call.
    initiate_config()

    key = "SWG"

    if cfg.args.test:
        test()
        exit()

    jira, username = jiralogin.get_jira_instance(cfg.args.t)

    if cfg.args.project:
        key = cfg.args.project


    # Open and initialize the file
    f = open_file(key + ".mm")
    root_nodes_start(f, key)

    # Temporary dictorionary to keep track the data (issues) that we already
    # have dealt with.
    d_handled = {}

    # Build the main tree with Initiatives beloninging to the project.
    nodes = build_initiatives_tree(jira, key, d_handled)

    # Take care of the orphans, i.e., those who has no connection to any
    # initiative in your project.
    nodes_orpans  = build_orphans_tree(jira, key, d_handled)

    # FIXME: We run through this once more since, when we run it the first time
    # we will catch Epics and Stories who are not linked with
    # "implements/implemented by" but instead uses the so called "Epic" link.
    nodes_orpans  = build_orphans_tree(jira, key, d_handled)

    # Dump the main tree to file
    for n in sorted(nodes):
        n.to_xml(f)

    orphan_node_start(f)
    for n in sorted(nodes_orpans):
        n.to_xml(f)
    orphan_node_end(f)

    # End the file
    root_nodes_end(f)
    f.close()

if __name__ == "__main__":
    main()
