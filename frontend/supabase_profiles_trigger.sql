-- Create profiles table if not exists
create table if not exists profiles (
  id uuid references auth.users on delete cascade not null primary key,
  email text,
  name text,
  role text,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Enable RLS on profiles
alter table profiles enable row level security;

-- Policy: Users can read their own profile
create policy "Users can read own profile"
on profiles for select
to authenticated
using (auth.uid() = id);

-- Policy: Users can update their own profile
create policy "Users can update own profile"
on profiles for update
to authenticated
using (auth.uid() = id);

-- Policy: Users can insert their own profile (only if creating)
create policy "Users can insert own profile"
on profiles for insert
to authenticated
with check (auth.uid() = id);

-- Function to automatically create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, name, role)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'name',
    new.raw_user_meta_data->>'role'
  );
  return new;
end;
$$ language plpgsql security definer;

-- Trigger to call function on new user signup
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
