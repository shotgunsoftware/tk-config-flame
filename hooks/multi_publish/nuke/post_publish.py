# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys

import tank
from tank import Hook
from tank import TankError

class PostPublishHookNukeFlame(Hook):
    """
    Single hook that implements post-publish functionality
    """    
    def execute(self, work_template, primary_task, secondary_tasks, progress_cb, **kwargs):
        """
        Main hook entry point
        
        :param work_template:   template
                                This is the template defined in the config that
                                represents the current work file

        :param primary_task:    The primary task that was published by the primary publish hook.  Passed
                                in here for reference.

        :param secondary_tasks: The list of secondary taskd that were published by the secondary 
                                publish hook.  Passed in here for reference.
                        
        :param progress_cb:     Function
                                A progress callback to log progress during pre-publish.  Call:
                        
                                    progress_cb(percentage, msg)
                             
                                to report progress to the UI

        :returns:               None
        :raises:                Raise a TankError to notify the user of a problem
        """
        import nuke
        
        progress_cb(0, "Versioning up the script")
        
        # get the current script path:
        original_path = nuke.root().name()
        script_path = os.path.abspath(original_path.replace("/", os.path.sep))
        
        # increment version and construct new name:
        progress_cb(25, "Finding next version number")
        fields = work_template.get_fields(script_path)
        next_version = self._get_next_work_file_version(work_template, fields)
        fields["version"] = next_version 
        new_path = work_template.apply_fields(fields)
        
        # log info
        self.parent.log_debug("Version up work file %s --> %s..." % (script_path, new_path))

        # rename script:
        nuke.root()["name"].setValue(new_path)
        
        # update write nodes:
        write_node_app = tank.platform.current_engine().apps.get("tk-nuke-writenode")
        if write_node_app:
            # only need to forceably reset the write node render paths if the app version
            # is less than or equal to v0.1.11
            from distutils.version import LooseVersion
            if (write_node_app.version != "Undefined" 
                and LooseVersion(write_node_app.version) <= LooseVersion("v0.1.11")):
                progress_cb(50, "Resetting render paths for write nodes")
                # reset render paths for all write nodes:
                for wn in write_node_app.get_write_nodes():
                    write_node_app.reset_node_render_path(wn)
                        
        # save the script:
        progress_cb(75, "Saving the scene file")
        nuke.scriptSaveAs(new_path.replace(os.path.sep, "/"))
        
        progress_cb(100)


    def _get_next_work_file_version(self, work_template, fields):
        """
        Find the next available version for the specified work_file
        """
        existing_versions = self.parent.tank.paths_from_template(work_template, fields, ["version"])
        version_numbers = [work_template.get_fields(v).get("version") for v in existing_versions]
        curr_v_no = fields["version"]
        max_v_no = max(version_numbers)
        return max(curr_v_no, max_v_no) + 1

