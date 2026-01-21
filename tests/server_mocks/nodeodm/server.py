import json
from werkzeug.wrappers import Request, Response
from faker import Faker

from ..base import MockedHTTPServer
from ..utils import jsonify, route
from .odm_utils import MockODMTaskManager, MockODMAssetFactory

fake = Faker()

class NodeODMMockHTTPServer(MockedHTTPServer):
    def __init__(self, httpserver):
        super().__init__(httpserver)
        self.manager = MockODMTaskManager()

    def _get_params(self, request: Request) -> dict:
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        if isinstance(data.get("options"), str):
            try:
                data["options"] = json.loads(data["options"])
            except (json.JSONDecodeError, TypeError):
                pass
        return data

    def _get_uuid(self, request: Request) -> str:
        return request.headers.get("set-uuid") or str(fake.uuid4())

    def _task_not_found(self):
        return jsonify({"error": "Task not found"}, status=200)

    # ------------------------------
    # SERVER INFO / OPTIONS
    # ------------------------------

    @route("/info", method="GET")
    def info(self, request: Request):
        return jsonify({
            "version": "2.3.2",
            "taskQueueCount": self.manager.get_queue_count(),
            "availableMemory": 8_000_000_000,
            "totalMemory": 16_000_000_000,
            "cpuCores": 4,
            "engineVersion": "3.0.0",
            "engine": "odm",
        })

    @route("/options", method="GET")
    def get_options(self, request: Request):
        return jsonify([{
            "name": "dsm",
            "type": "bool",
            "value": "false",
            "domain": "bool",
            "help": "Generate DSM",
        }])

    # ------------------------------
    # TASK CREATION
    # ------------------------------

    @route("/task/new/init", method="POST")
    def task_new_init(self, request: Request):
        uuid = self._get_uuid(request)
        params = self._get_params(request)
        self.manager.create_init(uuid, params.get("name"), params.get("options", []))
        return jsonify({"uuid": uuid})

    @route("/task/new", method="POST")
    def task_new_shortcut(self, request: Request):
        uuid = self._get_uuid(request)
        params = self._get_params(request)
        self.manager.create_shortcut(uuid, params.get("name"))
        return jsonify({"uuid": uuid})

    @route("/task/new/upload/{uuid}", method="POST")
    def task_upload(self, request: Request, uuid: str):
        if not (task := self.manager.get_task(uuid)):
            return self._task_not_found()

        images = request.files.getlist("images")
        task.imagesCount += len(images)
        task.add_log(f"Received {len(images)} images.")
        return jsonify({"success": True})

    @route("/task/new/commit/{uuid}", method="POST")
    def task_commit(self, request: Request, uuid: str):
        if not (task := self.manager.get_task(uuid)):
            return self._task_not_found()
        
        task.commit() # Triggered on model
        return jsonify({"uuid": uuid})

    # ------------------------------
    # TASK INFO / OUTPUT / DOWNLOAD
    # ------------------------------

    @route("/task/list", method="GET")
    def task_list(self, request: Request):
        return jsonify([{"uuid": u} for u in self.manager.list_uuids()])

    @route("/task/{uuid}/info", method="GET")
    def task_info(self, request: Request, uuid: str):
        task = self.manager.get_task(uuid)
        if not task: return self._task_not_found()

        with_output = int(request.args.get("with_output", 0))
        data = task.to_dict()
        if with_output:
            data["output"] = task.output[with_output:]
        return jsonify(data)

    @route("/task/{uuid}/output", method="GET")
    def task_output(self, request: Request, uuid: str):
        task = self.manager.get_task(uuid)
        if not task: return self._task_not_found()

        line = int(request.args.get("line", 0))
        # PyODM's output() method expects a JSON list of strings
        return jsonify(task.output[line:])

    @route("/task/{uuid}/download/all.zip", method="GET")
    def task_download_all(self, request: Request, uuid: str):
        if not self.manager.get_task(uuid):
            return self._task_not_found()

        return Response(
            ODMAssetFactory.create_zip(),
            mimetype="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{uuid}_all.zip"'}
        )

    # ------------------------------
    # TASK CONTROL
    # ------------------------------

    @route("/task/cancel", method="POST")
    def task_cancel(self, request: Request):
        params = self._get_params(request)
        task = self.manager.get_task(params.get("uuid"))
        if not task:
            return jsonify({"success": False}) # pyodm cancel logic
        
        task.cancel() # Logic on model
        return jsonify({"success": True})

    @route("/task/remove", method="POST")
    def task_remove(self, request: Request):
        params = self._get_params(request)
        success = self.manager.remove(params.get("uuid"))
        return jsonify({"success": success})

    @route("/task/restart", method="POST")
    def task_restart(self, request: Request):
        params = self._get_params(request)
        task = self.manager.get_task(params.get("uuid"))
        if not task:
            return jsonify({"success": False})

        task.restart(options=params.get("options"))
        return jsonify({"success": True})
