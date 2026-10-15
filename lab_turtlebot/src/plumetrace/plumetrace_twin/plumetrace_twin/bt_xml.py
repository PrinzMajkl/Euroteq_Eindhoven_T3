"""Nav2 behaviour tree for navigate_to_pose with a short BackUp recovery (or none).

Nav2's default tree (navigate_to_pose_w_replanning_and_recovery.xml) backs up 0.30 m when the robot is stuck. The
lidar cannot see the taped river and nothing checks behind the robot, so with an obstacle on the bank the robot
reversed into the river (lab 2026-10-15). Since 2026-10-15 (user's decision) lab_nav.launch.py keeps BackUp but
shortens it to backup_dist (default 0.15 m) so the robot can back off an obstacle and replan; backup_dist:=0 removes
BackUp as before. The other recoveries (clear costmaps, spin on the spot, wait) stay.
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


def set_backup(src, dst, dist, speed=None):
    """Copy the tree in src to dst with every BackUp node set to backup_dist=dist (and backup_speed). Returns the count."""
    tree = ET.parse(src)
    n = 0
    for node in tree.getroot().iter('BackUp'):
        node.set('backup_dist', f'{dist:g}')
        if speed is not None:
            node.set('backup_speed', f'{speed:g}')
        n += 1
    tree.write(dst, encoding='unicode')
    return n


def backup_params(share_dir, out_dir, dist, speed=0.05):
    """bt_navigator parameters for a tree whose BackUp backs up dist metres; dist <= 0 removes BackUp."""
    if dist <= 0:
        return no_backup_params(share_dir, out_dir)
    src = os.path.join(share_dir, *DEFAULT_TREE[1:])
    dst = os.path.join(out_dir, 'plumetrace_navigate_to_pose_backup.xml')
    try:
        if set_backup(src, dst, dist, speed) == 0:
            return {}
    except (OSError, ET.ParseError):
        return {}
    return {'default_nav_to_pose_bt_xml': dst}


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
