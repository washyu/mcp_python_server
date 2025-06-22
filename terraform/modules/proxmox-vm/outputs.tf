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

output "vm_status" {
  description = "Current status of the VM"
  value       = proxmox_virtual_environment_vm.vm.status
}

output "vm_resource" {
  description = "Complete VM resource information"
  value = {
    id          = proxmox_virtual_environment_vm.vm.vm_id
    name        = proxmox_virtual_environment_vm.vm.name
    node_name   = proxmox_virtual_environment_vm.vm.node_name
    status      = proxmox_virtual_environment_vm.vm.status
    tags        = proxmox_virtual_environment_vm.vm.tags
    description = proxmox_virtual_environment_vm.vm.description
    cpu_cores   = var.cpu_cores
    memory_mb   = var.memory_mb
    created_at  = timestamp()
  }
}