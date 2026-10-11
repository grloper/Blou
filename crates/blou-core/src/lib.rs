//! Portable product logic. Protocol engines and Android bindings live outside this crate.
//!
//! Portable Python cases have Rust counterparts. Python remains the reference until retirement approval.

pub mod dvc;
pub mod layout;
pub mod pin;
pub mod viewport;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CoreError(pub &'static str);

impl std::fmt::Display for CoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.0)
    }
}
impl std::error::Error for CoreError {}
