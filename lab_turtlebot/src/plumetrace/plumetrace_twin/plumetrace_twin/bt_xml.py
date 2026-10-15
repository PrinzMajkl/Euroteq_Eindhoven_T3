"""Nav2 behaviour tree for navigate_to_pose without the BackUp recovery.

Nav2's default tree (navigate_to_pose_w_replanning_and_recovery.xml) backs up 0.30 m when the robot is stuck. The
lidar cannot see the taped river and nothing checks behind the robot, so with an obstacle on the bank the robot
reversed into the river (lab 2026-10-15). lab_nav.launch.py writes the installed default tree without BackUp and
gives it to bt_navigator; the other recoveries (clear costmaps, spin on the spot, wait) stay.
"""
import os
import xml.etree.ElementTree as ET

DEFAULT_TREE = ('nav2_bt_navigator', 'behavior_trees', 'navigate_to_pose_w_replanning_and_recovery.xml')


def strip_backup(src, dst):
    """Copy the tree in src to dst without any BackUp node. Returns the number of nodes removed."""
    tree = ET.parse(src)
    removed = 0
    for parent in tree.getroot().iter():
        for child in list(parent):
            if child.tag == 'BackUp':
                parent.remove(child)
                removed += 1
    tree.write(dst, encoding='unicode')
    return removed


def no_backup_params(share_dir, out_dir):
    """bt_navigator parameters that select the tree without BackUp; {} (Nav2's default) when that is not possible."""
    src = os.path.join(share_dir, *DEFAULT_TREE[1:])
    dst = os.path.join(out_dir, 'plumetrace_navigate_to_pose_no_backup.xml')
    try:
        if strip_backup(src, dst) == 0:
            return {}
    except (OSError, ET.ParseError):
        return {}
    return {'default_nav_to_pose_bt_xml': dst}
