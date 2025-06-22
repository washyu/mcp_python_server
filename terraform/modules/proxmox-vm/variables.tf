variable "vm_name" {
  description = "Name of the virtual machine"
  type        = string
}

variable "vm_description" {
  description = "Description of the virtual machine"
  type        = string
  default     = "VM created by MCP Homelab Server"
}

variable "vm_tags" {
  description = "Tags to apply to the VM"
  type        = list(string)
  default     = ["mcp-managed", "homelab"]
}

variable "target_node" {
  description = "Proxmox node to deploy the VM on"
  type        = string
}

variable "pool_id" {
  description = "Resource pool ID (optional)"
  type        = string
  default     = null
}

variable "template_id" {
  description = "Template VM ID to clone from"
  type        = number
  default     = 9000
}

variable "cpu_cores" {
  description = "Number of CPU cores"
  type        = number
  default     = 2
}

variable "cpu_sockets" {
  description = "Number of CPU sockets"
  type        = number
  default     = 1
}

variable "cpu_type" {
  description = "CPU type (host, kvm64, etc.)"
  type        = string
  default     = "host"
}

variable "memory_mb" {
  description = "Memory in MB"
  type        = number
  default     = 2048
}

variable "disks" {
  description = "List of disks to attach to the VM"
  type = list(object({
    datastore_id = string
    size_gb      = number
    interface    = string
    file_format  = string
  }))
  default = [
    {
      datastore_id = "local-lvm"
      size_gb      = 20
      interface    = "scsi0"
      file_format  = "raw"
    }
  ]
}

variable "network_devices" {
  description = "List of network devices"
  type = list(object({
    bridge  = string
    model   = string
    vlan_id = optional(number)
  }))
  default = [
    {
      bridge  = "vmbr0"
      model   = "virtio"
      vlan_id = null
    }
  ]
}

variable "ip_config" {
  description = "IP configuration for cloud-init"
  type = object({
    address = string
    gateway = string
  })
  default = {
    address = "dhcp"
    gateway = null
  }
}

variable "cloud_init_user" {
  description = "Cloud-init default user"
  type        = string
  default     = "ansible-admin"
}

variable "cloud_init_password" {
  description = "Cloud-init user password (hashed)"
  type        = string
  sensitive   = true
}

variable "ssh_keys" {
  description = "List of SSH public keys"
  type        = list(string)
  default     = []
}

variable "cloud_init_user_data_file_id" {
  description = "Cloud-init user data file ID"
  type        = string
  default     = null
}

variable "start_vm" {
  description = "Start the VM after creation"
  type        = bool
  default     = true
}

variable "os_type" {
  description = "Operating system type"
  type        = string
  default     = "l26"
}

variable "scsi_hardware" {
  description = "SCSI hardware type"
  type        = string
  default     = "virtio-scsi-pci"
}

variable "machine_type" {
  description = "Machine type"
  type        = string
  default     = "q35"
}