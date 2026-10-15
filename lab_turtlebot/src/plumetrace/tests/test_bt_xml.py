import xml.etree.ElementTree as ET

from plumetrace_twin.bt_xml import backup_params, no_backup_params, set_backup, strip_backup

# Nav2 Jazzy navigate_to_pose_w_replanning_and_recovery.xml (recovery part as shipped)
TREE = """<root BTCPP_format="4" main_tree_to_execute="MainTree">
  <BehaviorTree ID="MainTree">
    <RecoveryNode number_of_retries="6" name="NavigateRecovery">
      <PipelineSequence name="NavigateWithReplanning">
        <RecoveryNode number_of_retries="1" name="FollowPath">
          <FollowPath path="{path}" controller_id="{selected_controller}"/>
          <ClearEntireCostmap name="ClearLocalCostmap-Context" service_name="local_costmap/clear_entirely_local_costmap"/>
        </RecoveryNode>
      </PipelineSequence>
      <ReactiveFallback name="RecoveryFallback">
        <GoalUpdated/>
        <RoundRobin name="RecoveryActions">
          <Sequence name="ClearingActions">
            <ClearEntireCostmap name="ClearLocalCostmap-Subtree" service_name="local_costmap/clear_entirely_local_costmap"/>
          </Sequence>
          <Spin spin_dist="1.57" error_code_id="{spin_error_code}"/>
          <Wait wait_duration="5.0"/>
          <BackUp backup_dist="0.30" backup_speed="0.05" error_code_id="{backup_error_code}"/>
        </RoundRobin>
      </ReactiveFallback>
    </RecoveryNode>
  </BehaviorTree>
</root>
"""


def test_strip_backup(tmp_path):
    src, dst = tmp_path / 'in.xml', tmp_path / 'out.xml'
    src.write_text(TREE)
    assert strip_backup(str(src), str(dst)) == 1
    root = ET.parse(dst).getroot()
    assert not list(root.iter('BackUp'))
    rr = next(root.iter('RoundRobin'))
    assert [c.tag for c in rr] == ['Sequence', 'Spin', 'Wait']
    assert root.get('BTCPP_format') == '4'


def test_no_backup_params(tmp_path):
    share = tmp_path / 'share'
    (share / 'behavior_trees').mkdir(parents=True)
    (share / 'behavior_trees' / 'navigate_to_pose_w_replanning_and_recovery.xml').write_text(TREE)
    p = no_backup_params(str(share), str(tmp_path))
    assert p['default_nav_to_pose_bt_xml'].endswith('_no_backup.xml')
    assert no_backup_params(str(tmp_path / 'missing'), str(tmp_path)) == {}


def test_set_backup(tmp_path):
    src, dst = tmp_path / 'in.xml', tmp_path / 'out.xml'
    src.write_text(TREE)
    assert set_backup(str(src), str(dst), 0.15) == 1
    b = next(ET.parse(dst).getroot().iter('BackUp'))
    assert b.get('backup_dist') == '0.15' and b.get('backup_speed') == '0.05'


def test_backup_params(tmp_path):
    share = tmp_path / 'share'
    (share / 'behavior_trees').mkdir(parents=True)
    (share / 'behavior_trees' / 'navigate_to_pose_w_replanning_and_recovery.xml').write_text(TREE)
    p = backup_params(str(share), str(tmp_path), 0.15)
    assert p['default_nav_to_pose_bt_xml'].endswith('_backup.xml')
    assert next(ET.parse(p['default_nav_to_pose_bt_xml']).getroot().iter('BackUp')).get('backup_dist') == '0.15'
    off = backup_params(str(share), str(tmp_path), 0.0)
    assert off['default_nav_to_pose_bt_xml'].endswith('_no_backup.xml')
    assert backup_params(str(tmp_path / 'missing'), str(tmp_path), 0.15) == {}
