terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.66.0"
    }
  }
}

resource "proxmox_virtual_environment_vm" "vm" {
  name        = var.vm_name
  description = var.vm_description
  tags        = var.vm_tags
  node_name   = var.target_node
  pool_id     = var.pool_id

  # Clone from template
  clone {
    vm_id = var.template_id
  }

  # CPU configuration
  cpu {
    cores   = var.cpu_cores
    sockets = var.cpu_sockets
    type    = var.cpu_type
  }

  # Memory configuration
  memory {
    dedicated = var.memory_mb
  }

  # Disk configuration
  dynamic "disk" {
    for_each = var.disks
    content {
      datastore_id = disk.value.datastore_id
      size         = disk.value.size_gb
      interface    = disk.value.interface
      file_format  = disk.value.file_format
    }
  }

  # Network configuration
  dynamic "network_device" {
    for_each = var.network_devices
    content {
      bridge  = network_device.value.bridge
      model   = network_device.value.model
      vlan_id = network_device.value.vlan_id
    }
  }

  # Cloud-init configuration
  initialization {
    ip_config {
      ipv4 {
        address = var.ip_config.address
        gateway = var.ip_config.gateway
      }
    }

    user_account {
      username = var.cloud_init_user
      password = var.cloud_init_password
      keys     = var.ssh_keys
    }

    user_data_file_id = var.cloud_init_user_data_file_id
  }

  # Start VM after creation
  started = var.start_vm

  # QEMU guest agent
  agent {
    enabled = true
    trim    = true
    type    = "virtio"
  }

  # VGA configuration for console access
  vga {
    type = "serial0"
  }

  # Serial device for console
  serial_device {}

  # Operating system type
  operating_system {
    type = var.os_type
  }

  # SCSI hardware type
  scsi_hardware = var.scsi_hardware

  # Machine type
  machine = var.machine_type

  # Lifecycle management
  lifecycle {
    ignore_changes = [
      # Ignore changes to these attributes after creation
      initialization[0].user_data_file_id,
    ]
  }
}

# Output important VM information
output "vm_id" {
  description = "The ID of the created VM"
  value       = proxmox_virtual_environment_vm.vm.vm_id
}

output "vm_name" {
  description = "The name of the created VM"
  value       = proxmox_virtual_environment_vm.vm.name
}

output "node_name" {
  description = "The node where the VM is deployed"
  value       = proxmox_virtual_environment_vm.vm.node_name
}

output "vm_tags" {
  description = "Tags applied to the VM"
  value       = proxmox_virtual_environment_vm.vm.tags
}