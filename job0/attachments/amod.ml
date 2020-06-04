(*print_string "Hello world";;*)

module Amod = struct
  type 'a btree =
      Nil
    | Btree of 'a * 'a btree * 'a btree

  let x = 123
end;;