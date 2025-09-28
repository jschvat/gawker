from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime

from .models import *
from ..core.daemon import ProcessGuardDaemon
from ..core.app_wizard import AppWizard
from ..models.process import ProcessConfig, ProcessType
from ..utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

daemon_instance: Optional[ProcessGuardDaemon] = None

def get_daemon() -> ProcessGuardDaemon:
    if daemon_instance is None:
        raise HTTPException(status_code=500, detail="Daemon not initialized")
    return daemon_instance

def set_daemon(daemon: ProcessGuardDaemon):
    global daemon_instance
    daemon_instance = daemon

@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@router.get("/processes", response_model=List[ProcessStatusResponse])
async def list_processes(daemon: ProcessGuardDaemon = Depends(get_daemon)):
    processes = []
    for name, process in daemon.process_manager.get_all_processes().items():
        latest_metrics = process.get_latest_metrics()

        processes.append(ProcessStatusResponse(
            name=name,
            status=process.status,
            pid=process.pid,
            started_at=process.started_at,
            restart_count=process.restart_count,
            config=ProcessConfigCreate(
                name=process.config.name,
                command=process.config.command,
                working_dir=process.config.working_dir,
                process_type=process.config.process_type,
                env_vars=process.config.env_vars,
                auto_restart=process.config.auto_restart,
                max_restarts=process.config.max_restarts,
                restart_delay=process.config.restart_delay,
                log_file=process.config.log_file,
                redirect_output=process.config.redirect_output,
                cpu_limit=process.config.cpu_limit,
                memory_limit=process.config.memory_limit,
                alert_on_failure=process.config.alert_on_failure,
                alert_on_high_cpu=process.config.alert_on_high_cpu,
                alert_on_high_memory=process.config.alert_on_high_memory,
                cpu_threshold=process.config.cpu_threshold,
                memory_threshold=process.config.memory_threshold
            ),
            latest_metrics=ProcessMetricsResponse(
                timestamp=latest_metrics.timestamp,
                pid=latest_metrics.pid,
                cpu_percent=latest_metrics.cpu_percent,
                memory_percent=latest_metrics.memory_percent,
                memory_mb=latest_metrics.memory_mb,
                open_files=latest_metrics.open_files,
                connections=latest_metrics.connections,
                threads=latest_metrics.threads,
                status=latest_metrics.status,
                uptime=latest_metrics.uptime
            ) if latest_metrics else None
        ))

    return processes

@router.post("/processes", response_model=ApiResponse)
async def create_process(
    process_config: ProcessConfigCreate,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    try:
        config = ProcessConfig(
            name=process_config.name,
            command=process_config.command,
            working_dir=process_config.working_dir,
            process_type=ProcessType(process_config.process_type.value),
            env_vars=process_config.env_vars,
            auto_restart=process_config.auto_restart,
            max_restarts=process_config.max_restarts,
            restart_delay=process_config.restart_delay,
            log_file=process_config.log_file,
            redirect_output=process_config.redirect_output,
            cpu_limit=process_config.cpu_limit,
            memory_limit=process_config.memory_limit,
            alert_on_failure=process_config.alert_on_failure,
            alert_on_high_cpu=process_config.alert_on_high_cpu,
            alert_on_high_memory=process_config.alert_on_high_memory,
            cpu_threshold=process_config.cpu_threshold,
            memory_threshold=process_config.memory_threshold
        )

        success = daemon.add_process(config)
        if success:
            return ApiResponse(success=True, message=f"Process {process_config.name} created successfully")
        else:
            raise HTTPException(status_code=400, detail="Failed to create process")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/processes/{process_name}", response_model=ProcessStatusResponse)
async def get_process(
    process_name: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    status = daemon.get_process_status(process_name)
    if not status:
        raise HTTPException(status_code=404, detail="Process not found")

    process = daemon.process_manager.processes[process_name]
    latest_metrics = process.get_latest_metrics()

    return ProcessStatusResponse(
        name=process_name,
        status=process.status,
        pid=process.pid,
        started_at=process.started_at,
        restart_count=process.restart_count,
        config=ProcessConfigCreate(
            name=process.config.name,
            command=process.config.command,
            working_dir=process.config.working_dir,
            process_type=process.config.process_type,
            env_vars=process.config.env_vars,
            auto_restart=process.config.auto_restart,
            max_restarts=process.config.max_restarts,
            restart_delay=process.config.restart_delay,
            log_file=process.config.log_file,
            redirect_output=process.config.redirect_output,
            cpu_limit=process.config.cpu_limit,
            memory_limit=process.config.memory_limit,
            alert_on_failure=process.config.alert_on_failure,
            alert_on_high_cpu=process.config.alert_on_high_cpu,
            alert_on_high_memory=process.config.alert_on_high_memory,
            cpu_threshold=process.config.cpu_threshold,
            memory_threshold=process.config.memory_threshold
        ),
        latest_metrics=ProcessMetricsResponse(
            timestamp=latest_metrics.timestamp,
            pid=latest_metrics.pid,
            cpu_percent=latest_metrics.cpu_percent,
            memory_percent=latest_metrics.memory_percent,
            memory_mb=latest_metrics.memory_mb,
            open_files=latest_metrics.open_files,
            connections=latest_metrics.connections,
            threads=latest_metrics.threads,
            status=latest_metrics.status,
            uptime=latest_metrics.uptime
        ) if latest_metrics else None
    )

@router.post("/processes/{process_name}/start", response_model=ApiResponse)
async def start_process(
    process_name: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    success = daemon.start_process(process_name)
    if success:
        return ApiResponse(success=True, message=f"Process {process_name} started successfully")
    else:
        raise HTTPException(status_code=400, detail="Failed to start process")

@router.post("/processes/{process_name}/stop", response_model=ApiResponse)
async def stop_process(
    process_name: str,
    force: bool = False,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    success = daemon.stop_process(process_name, force)
    if success:
        return ApiResponse(success=True, message=f"Process {process_name} stopped successfully")
    else:
        raise HTTPException(status_code=400, detail="Failed to stop process")

@router.post("/processes/{process_name}/restart", response_model=ApiResponse)
async def restart_process(
    process_name: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    success = daemon.restart_process(process_name)
    if success:
        return ApiResponse(success=True, message=f"Process {process_name} restarted successfully")
    else:
        raise HTTPException(status_code=400, detail="Failed to restart process")

@router.delete("/processes/{process_name}", response_model=ApiResponse)
async def delete_process(
    process_name: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    success = daemon.remove_process(process_name)
    if success:
        return ApiResponse(success=True, message=f"Process {process_name} deleted successfully")
    else:
        raise HTTPException(status_code=404, detail="Process not found")

@router.get("/system/info", response_model=SystemInfoResponse)
async def get_system_info(daemon: ProcessGuardDaemon = Depends(get_daemon)):
    system_status = daemon.get_system_status()
    return SystemInfoResponse(**system_status["system_info"])

@router.get("/system/metrics", response_model=SystemMetricsResponse)
async def get_system_metrics(daemon: ProcessGuardDaemon = Depends(get_daemon)):
    system_status = daemon.get_system_status()
    return SystemMetricsResponse(**system_status["system_metrics"])

@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    active_only: bool = True,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    alerts = daemon.get_alerts(active_only)
    return [AlertResponse(**alert) for alert in alerts]

@router.post("/alerts/{alert_id}/acknowledge", response_model=ApiResponse)
async def acknowledge_alert(
    alert_id: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    success = daemon.alert_manager.acknowledge_alert(alert_id)
    if success:
        return ApiResponse(success=True, message=f"Alert {alert_id} acknowledged")
    else:
        raise HTTPException(status_code=404, detail="Alert not found")

@router.post("/alerts/{alert_id}/resolve", response_model=ApiResponse)
async def resolve_alert(
    alert_id: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    success = daemon.alert_manager.resolve_alert(alert_id)
    if success:
        return ApiResponse(success=True, message=f"Alert {alert_id} resolved")
    else:
        raise HTTPException(status_code=404, detail="Alert not found")

@router.get("/processes/{process_name}/logs", response_model=List[LogFileResponse])
async def get_process_log_files(
    process_name: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    log_files = daemon.log_manager.list_log_files(process_name)
    return [LogFileResponse(**log_file) for log_file in log_files]

@router.get("/processes/{process_name}/logs/recent")
async def get_recent_logs(
    process_name: str,
    lines: int = 100,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    logs = daemon.log_manager.get_recent_logs(process_name, lines)
    return {"logs": logs}

@router.get("/processes/{process_name}/logs/stream")
async def stream_logs(
    process_name: str,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    async def generate():
        async for line in daemon.log_manager.get_log_stream(process_name):
            yield f"data: {json.dumps({'line': line, 'timestamp': datetime.now().isoformat()})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    daemon = get_daemon()

    try:
        while True:
            system_status = daemon.get_system_status()

            processes_status = {}
            for name, process in daemon.process_manager.get_all_processes().items():
                metrics = daemon.process_manager.get_process_metrics(name)
                if metrics:
                    processes_status[name] = {
                        "status": process.status.value,
                        "cpu_percent": metrics.cpu_percent,
                        "memory_percent": metrics.memory_percent,
                        "memory_mb": metrics.memory_mb,
                        "uptime": metrics.uptime
                    }

            data = {
                "timestamp": datetime.now().isoformat(),
                "system": system_status["system_metrics"],
                "processes": processes_status,
                "alerts": daemon.get_alerts(active_only=True)
            }

            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(5)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")

# App Wizard Endpoints
@router.post("/wizard/analyze", response_model=WizardProjectAnalysisResponse)
async def analyze_project(
    request: WizardProjectAnalysisRequest,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    """Analyze a project directory and suggest configuration"""
    try:
        wizard = AppWizard()
        analysis = await wizard.analyze_project(request.project_path)

        return WizardProjectAnalysisResponse(
            app_type=analysis['app_type'],
            detected_frameworks=analysis['frameworks'],
            package_managers=analysis['package_managers'],
            suggested_commands=analysis['suggested_commands'],
            environment_variables=analysis['environment_variables'],
            monitoring_patterns=analysis['monitoring_patterns'],
            ports=analysis['ports'],
            dependencies=analysis['dependencies']
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze project: {str(e)}")

@router.post("/wizard/generate-scripts", response_model=WizardScriptGenerationResponse)
async def generate_scripts(
    request: WizardScriptGenerationRequest,
    daemon: ProcessGuardDaemon = Depends(get_daemon)
):
    """Generate launch and kill scripts for a project"""
    try:
        wizard = AppWizard()

        # First analyze the project if needed
        analysis = await wizard.analyze_project(request.project_path)

        # Generate launch script
        launch_script = await wizard.generate_launch_script(
            project_path=request.project_path,
            app_type=request.app_type,
            process_name=request.process_name,
            environment=request.environment,
            custom_command=request.custom_command,
            custom_env_vars=request.custom_env_vars,
            custom_ports=request.custom_ports
        )

        # Generate kill script
        kill_script = await wizard.generate_kill_script(
            project_path=request.project_path,
            app_type=request.app_type,
            process_name=request.process_name,
            environment=request.environment
        )

        # Generate ProcessGuard configuration
        process_config = {
            "name": request.process_name,
            "command": request.custom_command or analysis['suggested_commands'].get('start', ''),
            "working_dir": request.project_path,
            "process_type": "nodejs" if request.app_type in ["react", "nextjs", "nodejs", "express"] else "generic",
            "env_vars": {**analysis['environment_variables'], **(request.custom_env_vars or {})},
            "auto_restart": True,
            "max_restarts": 5,
            "restart_delay": 5 if request.environment == "development" else 10,
            "redirect_output": True,
            "cpu_threshold": 70.0 if request.environment == "development" else 80.0,
            "memory_threshold": 70.0 if request.environment == "development" else 80.0,
            "crash_policy": {
                "max_crashes": 8 if request.environment == "development" else 5,
                "time_window_minutes": 5 if request.environment == "development" else 10,
                "action_on_threshold": "quarantine" if request.environment == "development" else "disable"
            }
        }

        # Generate monitoring configuration
        monitoring_config = analysis['monitoring_patterns']

        return WizardScriptGenerationResponse(
            launch_script=launch_script,
            kill_script=kill_script,
            process_config=process_config,
            monitoring_config=monitoring_config
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to generate scripts: {str(e)}")

@router.get("/wizard/supported-types")
async def get_supported_app_types():
    """Get list of supported application types"""
    wizard = AppWizard()
    return {
        "supported_types": [
            {
                "type": "react",
                "name": "React Application",
                "description": "Create React App or Vite React project"
            },
            {
                "type": "nextjs",
                "name": "Next.js Application",
                "description": "Next.js React framework"
            },
            {
                "type": "nodejs",
                "name": "Node.js Application",
                "description": "Generic Node.js application"
            },
            {
                "type": "express",
                "name": "Express.js API",
                "description": "Express.js backend API"
            },
            {
                "type": "python",
                "name": "Python Application",
                "description": "Python application (Flask, FastAPI, Django)"
            },
            {
                "type": "flask",
                "name": "Flask Application",
                "description": "Flask web application"
            },
            {
                "type": "fastapi",
                "name": "FastAPI Application",
                "description": "FastAPI web application"
            },
            {
                "type": "go",
                "name": "Go Application",
                "description": "Go/Golang application"
            },
            {
                "type": "rust",
                "name": "Rust Application",
                "description": "Rust application"
            },
            {
                "type": "generic",
                "name": "Generic Application",
                "description": "Any other type of application"
            }
        ]
    }