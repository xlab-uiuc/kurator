function $id(id) {
    return document.getElementById(id);
}

/**************************************************************************
 * Monaco Editor
 *************************************************************************/
var code = "# Loading config...";
// dark theme
var originalModel = monaco.editor.createModel(code, 'yaml');
var modifiedModel = monaco.editor.createModel(code, 'yaml');
var dataPoints = []

var diffEditor = monaco.editor.createDiffEditor($id('diff-editor'), {
    enableSplitViewResizing: false,
    renderSideBySide: true,
    readOnly: false,
    theme: 'vs-dark',
    ignoreTrimWhitespace: false,
    originalEditable: true,
});
diffEditor.setModel({
    original: originalModel,
    modified: modifiedModel
});

var changeInstructionEditor = monaco.editor.create($id('change-instruction'), {
    language: 'yaml',
    theme: 'vs-dark',
    readOnly: false,
    automaticLayout: true,
    lineNumbers: 'off',
    minimap: {
        enabled: false
    },
    wordWrap: 'on',
});

var noteEditor = monaco.editor.create($id('note'), {
    language: 'yaml',
    theme: 'vs-dark',
    readOnly: false,
    automaticLayout: true,
    lineNumbers: 'off',
    minimap: {
        enabled: false
    },
    wordWrap: 'on',
});

function replaceEditorValueKeepingStack(editor, newText) {
    // https://github.com/microsoft/monaco-editor/issues/299
    editor.executeEdits(
        'gpt3', [{ identifier: 'delete', range: new monaco.Range(1, 1, 10000, 1), text: '', forceMoveMarkers: true }]);
    editor.executeEdits(
        'gpt3', [{ identifier: 'insert', range: new monaco.Range(1, 1, 1, 1), text: newText, forceMoveMarkers: true }]);
}

/**************************************************************************
 * GPT-3 - for suggestion instructions
 *************************************************************************/

async function load_completion() {
    if (diffEditor.getModel().modified.getValue().trim() === diffEditor.getModel().original.getValue().trim()) {
        alert("Please make some changes first.");
        return;
    }

    $id("spinner").style.display = "inline-block";

    var response = await fetch('/api/query_gpt3', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            before: originalModel.getValue(),
            after: modifiedModel.getValue()
        })
    })
    if (response.ok) {
        var data = await response.json();
        replaceEditorValueKeepingStack(changeInstructionEditor, data);
    } else {
        replaceEditorValueKeepingStack(changeInstructionEditor, "Error: " + response.status);
    }

    $id("spinner").style.display = "none";
}

$id('gpt3-suggest-btn').addEventListener('click', load_completion);

/**************************************************************************
 * GPT-3 - for suggestion new config
 *************************************************************************/

async function load_new_config() {
    // check change instruction is not empty
    if (changeInstructionEditor.getValue().trim() === "") {
        alert("Please write change instruction first.");
        return;
    }

    $id("spinner").style.display = "inline-block";

    var response = await fetch('/api/query_gpt3_new_config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            before: originalModel.getValue(),
            change_instruction: changeInstructionEditor.getValue()
        })
    });

    if (response.ok) {
        var data = await response.json();
        replaceEditorValueKeepingStack(diffEditor._modifiedEditor, data);
    } else {
        replaceEditorValueKeepingStack(diffEditor._modifiedEditor, "Error: " + response.status);
    }

    $id("spinner").style.display = "none";
}

$id('gpt3-suggest-conf-btn').addEventListener('click', load_new_config);

/**************************************************************************
 * Config Selector
 *************************************************************************/
// async function loadStarterConfigs() {
//     var response = await fetch('/api/get_starter_configs', {
//         method: 'GET',
//         headers: {
//             'Content-Type': 'application/json'
//         }
//     })
//     if (response.ok) {
//         var starterConfigs = await response.json();
//         var select = $id('config-selector');
//         select.innerHTML = '';
//         for (var key in starterConfigs) {
//             var option = document.createElement("option");
//             option.innerHTML = key;
//             option.value = key;
//             select.add(option);
//         }

//         select.addEventListener('change', function () {
//             var key = select.value;
//             if (key != -1) {
//                 replaceEditorValueKeepingStack(diffEditor._originalEditor, starterConfigs[key]);
//                 replaceEditorValueKeepingStack(diffEditor._modifiedEditor, starterConfigs[key]);
//             }
//         });

//         select.value = Object.keys(starterConfigs)[0];
//         select.dispatchEvent(new Event('change'));
//     } else {
//         alert("Error loading starter configs: " + response.status);
//     }
// }

// loadStarterConfigs();

/**************************************************************************
 * Data Selector
 *************************************************************************/

async function loadDataPoints() {
    var response = await fetch('/api/get_data_points', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    if (response.ok) {
        var isBrandNew = dataPoints.length === 0;
        dataPoints = await response.json();
        var select = $id('data-selector');
        var selectedDataPoint = select.value;
        select.innerHTML = '<option value="-1">Select a data point</option>';
        for (var i = 0; i < dataPoints.length; i++) {
            var option = document.createElement("option");
            option.innerHTML = (i + 1) + " - " + dataPoints[i]["username"];
            option.value = i;
            select.add(option);
        }

        if (isBrandNew) {
            select.addEventListener('change', function () {
                var key = select.value;
                if (key != -1) {
                    replaceEditorValueKeepingStack(diffEditor._originalEditor, dataPoints[key]['before_edit']);
                    replaceEditorValueKeepingStack(diffEditor._modifiedEditor, dataPoints[key]['after_edit']);
                    replaceEditorValueKeepingStack(changeInstructionEditor, dataPoints[key]['human_change_instruction']);
                    replaceEditorValueKeepingStack(noteEditor, dataPoints[key]['note'] || '');
                }
            });
        }

        if (selectedDataPoint == -1) {
            selectedDataPoint = Math.min("0", dataPoints.length - 1);
        }

        select.value = selectedDataPoint;
        select.dispatchEvent(new Event('change'));

    } else {
        alert("Error loading data points: " + response.status);
    }
}

loadDataPoints();

/**************************************************************************
 * Validate config
 *************************************************************************/

async function validate_configs() {
    var response = await fetch('/api/validate_configs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            before: originalModel.getValue(),
            after: modifiedModel.getValue()
        })
    })
    if (response.ok) {
        var data = await response.json();
        if (data.before_error || data.after_error) {
            //alert("Config(s) are invalid. Error: " + JSON.stringify(data));
            before_error = data.before_error || "Valid";
            after_error = data.after_error || "Valid";

            $id("errorModalBody").innerHTML = "Config(s) are invalid. Error:<br><br><code style='white-space: pre-wrap'><b>Original Config:</b>\n" + before_error + "\n\n<b>Modified Config:</b>\n" + after_error + "</code>";

            var errorModal = new bootstrap.Modal($id('errorModal'));
            errorModal.show();
            return false;
        } else if (data.validation_error) {
            $id("errorModalBody").innerHTML = "Unable to validate configurations. The issue has been logged on the server and will be fixed shortly.<br><strong>Please submit your data point anyway.</strong>";

            var errorModal = new bootstrap.Modal($id('errorModal'));
            errorModal.show();
        } else {
            return true;
        }
    } else {
        alert("Error while validating configs: " + response.status);
    }
}

$id('validate-btn').addEventListener('click', async function () {
    if (await validate_configs()) alert("Config(s) are valid.")
});

/**************************************************************************
 * Submit
 *************************************************************************/
async function submit(edit = false) {
    // sanity check
    if (diffEditor._originalEditor.getValue().trim() == diffEditor._modifiedEditor.getValue().trim()) {
        alert("The original and modified configs are the same. Please make a change.");
        return;
    }
    if (changeInstructionEditor.getValue().trim() == "") {
        alert("Please generate a change instruction.");
        return;
    }

    var id = null;
    if (edit) {
        id = dataPoints[$id('data-selector').value].id;
        if (!id) {
            alert("Error: data point id not found.");
            return;
        }

        if (!confirm("Are you sure you want to edit this data point? ID: " + id)) {
            return;
        }
    }

    // const is_valid = await validate_configs();
    // if (!is_valid) {
    //     return;
    // }

    // if (!edit) {
    //     alert("not saving due to debug, but config's valid");
    //     return;
    // }

    var response = await fetch('/api/add_data_point', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            id: id,
            username: "placeholder@placeholder.com",
            before_edit: originalModel.getValue(),
            after_edit: modifiedModel.getValue(),
            human_change_instruction: changeInstructionEditor.getValue(),
            note: noteEditor.getValue(),
        })
    })
    if (response.ok) {
        alert(edit ? "Edited!" : "Submitted!");
        loadDataPoints();
    } else {
        alert("Error submitting: " + response.status);
    }
}

$id('submit-btn').addEventListener('click', () => submit(false));
$id('edit-btn').addEventListener('click', () => submit(true));

/**************************************************************************
 * Delete
 *************************************************************************/

async function deleteDataPoint() {
    if (!confirm("Are you sure you want to delete this data point?")) {
        return;
    }

    if (!confirm("Are you really sure?")) {
        return;
    }

    var id = dataPoints[$id('data-selector').value].id;
    var response = await fetch('/api/del_data_point?data_point_id=' + id, {
        method: 'POST',
    })
    if (response.ok) {
        alert("Deleted!");
        loadDataPoints();
    } else {
        alert("Error deleting: " + response.status);
    }
}

$id('del-btn').addEventListener('click', deleteDataPoint);