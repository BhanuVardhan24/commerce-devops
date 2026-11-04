variable "private_subnet_ids" { type = list(string) }
variable "admin_role_arn" { type = string }
variable "admin_cidr" { type = string }
variable "addon_pins" {
  type    = map(string)
  default = {}
}
