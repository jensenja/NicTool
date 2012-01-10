#!/usr/bin/perl
#
# NicTool v2.00-rc1 Copyright 2001 Damon Edwards, Abe Shelton & Greg Schueler
# NicTool v2.01+ Copyright 2004-2008 The Network People, Inc.
#
# NicTool is free software; you can redistribute it and/or modify it under
# the terms of the Affero General Public License as published by Affero,
# Inc.; either version 1 of the License, or any later version.
#
# NicTool is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the Affero GPL for details.
#
# You should have received a copy of the Affero General Public License
# along with this program; if not, write to Affero Inc., 521 Third St,
# Suite 225, San Francisco, CA 94107, USA
#

use strict;

require 'nictoolclient.conf';

main();

sub main {
    my $q      = new CGI();
    my $nt_obj = new NicToolClient($q);

    return if $nt_obj->check_setup ne 'OK';

    my $user = $nt_obj->verify_session();

    if ($user) {
        print $q->header;
        display( $nt_obj, $q, $user );
    }
}

sub display {
    my ( $nt_obj, $q, $user ) = @_;

    $nt_obj->parse_template($NicToolClient::start_html_template);
    $nt_obj->parse_template(
        $NicToolClient::body_frame_start_template,
        username  => $user->{'username'},
        groupname => $user->{'groupname'},
        userid    => $user->{'nt_user_id'},
    );

    my $zone = $nt_obj->get_zone( nt_zone_id => $q->param('nt_zone_id') );

    my $level = $nt_obj->display_group_tree(
        $user,
        $user->{'nt_group_id'},
        $zone->{'delegated_by_id'} ? '' : $q->param('nt_group_id'), 0
    );

    if ( $zone->{'error_code'} ne 200 ) {
        $nt_obj->display_nice_error( $zone, "Get Zone" );
        return;
    }

    $nt_obj->display_zone_list_options( $user, $q->param('nt_group_id'), $level, 0 );
    $nt_obj->display_zone_options( $user, $zone, $level + 1, 0 );    #1);

    $zone = display_zone( $nt_obj, $user, $q, $zone );
    display_nameservers( $nt_obj, $user, $q, $zone );
    display_zone_records( $nt_obj, $user, $q, $zone );

    $nt_obj->parse_template($NicToolClient::end_html_template);
}

sub display_zone {
    my ( $nt_obj, $user, $q, $zone ) = @_;
    my $isdelegate = exists $zone->{'delegated_by_id'};
    if ( $q->param('edit_zone') ) {
        if ( $q->param('Save') ) {
            my @fields = qw/ nt_zone_id nt_group_id zone nameservers 
                description mailaddr serial refresh retry expire ttl minimum /;
            my %data = map { $_ => $q->param($_) } @fields;
            $data{'nameservers'} = join( ',', $q->param('nameservers') );
            $data{'deleted'} = 0 if $q->param('undelete');

            my $error = $nt_obj->edit_zone(%data);
            if ( $error->{'error_code'} != 200 ) {
                display_edit_zone( $nt_obj, $user, $q, $error, $zone, 'edit' );
            }
            else {
                $zone = $nt_obj->get_zone(
                    nt_group_id => $q->param('nt_group_id'),
                    nt_zone_id  => $q->param('nt_zone_id')
                );
            }
        }
        elsif ( $q->param('Cancel') ) {

        }
        else {
            display_edit_zone( $nt_obj, $user, $q, '', $zone, 'edit' );
        }
    }
    if ( $q->param('new_zone') ) {
        if ( $q->param('Create') ) {
            my @fields = qw/ nt_group_id zone nameservers description mailaddr 
                            serial refresh retry expire ttl minimum/;
            my %data = map { $_ => $q->param($_) } @fields;
            $data{'nameservers'} = join( ',', $q->param('nameservers') );

            my $error = $nt_obj->new_zone(%data);
            if ( $error->{'error_code'} != 200 ) {
                display_edit_zone( $nt_obj, $user, $q, $error, $zone, 'new' );
            }
            else {
                my $zid = $error->{'nt_zone_id'};
                if ($NicToolClient::edit_after_new_zone) {
                    $q->param( -name => 'object', -value => 'zone' );
                    $q->param( -name => 'obj_id', -value => $zid );
                    return $nt_obj->redirect_from_log($q);
                }
                $zone = $nt_obj->get_zone(
                    nt_group_id => $q->param('nt_group_id'),
                    nt_zone_id  => $zid,
                );
                if ( $zone->{'error_code'} != 200 ) {
                    $nt_obj->display_nice_error( $zone, "Get Zone" );
                }
            }
        }
        elsif ( $q->param('Cancel') ) { }
        else {
            display_edit_zone( $nt_obj, $user, $q, '', $zone, 'new' );
        }
    }

    if (   $q->param('deletedelegate')
        && $q->param('type') ne 'record'
        && $q->param('nt_zone_id')
        && $q->param('delegate_group_id') )
    {
        my $error = $nt_obj->delete_zone_delegation(
            nt_zone_id  => $q->param('nt_zone_id'),
            nt_group_id => $q->param('delegate_group_id')
        );
        if ( $error->{'error_code'} != 200 ) {
            $nt_obj->display_nice_error( $error, "Delete Zone Delegation" );
        }
        else {
            $nt_obj->display_nice_message(
                "The zone delegation was successfully removed.",
                "Delegation Removed" );
        }
    }
    elsif ($q->param('deletedelegate')
        && $q->param('type') eq 'record'
        && $q->param('nt_zone_record_id')
        && $q->param('delegate_group_id') )
    {
        my $error = $nt_obj->delete_zone_record_delegation(
            nt_zone_record_id => $q->param('nt_zone_record_id'),
            nt_group_id       => $q->param('delegate_group_id')
        );
        if ( $error->{'error_code'} != 200 ) {
            $nt_obj->display_nice_error( $error,
                "Delete Zone Record Delegation" );
        }
        else {
            $nt_obj->display_nice_message(
                "The resource record delegation was successfully removed.",
                "Delegation Removed" );
        }
    }

    display_zone_deleted() if $zone->{'deleted'};

    if ($isdelegate) {
        display_zone_delegate( $nt_obj, $q, $user, $zone );
    }
    else {
        display_zone_delegation( $nt_obj, $q, $user, $zone );
    };

    display_zone_properties( $nt_obj, $q, $zone, $user );

    return $zone;
}

sub display_zone_deleted {
        print qq[
<table id="zoneDeletedError" class="fat">
 <tr class=dark_grey_bg>
  <td class="fat light_grey_bg nowrap">
     This zone may not be modified because it is deleted.
  </td>
 </tr>
</table>
];
}

sub display_zone_delegate {
    my ( $nt_obj, $q, $user, $zone ) = @_;

    print qq[
<table id="delegationInfo" class="fat">
 <tr class=dark_grey_bg><td class="no_pad fat bold">Delegation</td></tr>
</table>

<table id="unSure" class="fat" style="spacing:0;">
 <tr>
  <td class="top">
   <table id="delegatedBy" class="fat">];

    if ( !$zone->{'pseudo'} ) {
        print qq[
    <tr class="light_grey_bg">
     <td class="nowrap"> Delegated by: </td>
     <td class="fat middle">
       <img src="$NicToolClient::image_dir/user.gif" alt="user"> $zone->{'delegated_by_name'}
     </td>
    </tr>];
    }
    else {
        print qq[
    <tr class=light_hilite_bg>
     <td class="nowrap" colspan=2> This zone is visible because some of its records have been delegated to you.</td>
    </tr>];

    }

    print qq[
     <tr class=light_grey_bg>
      <td class="nowrap"> Belonging to group: </td>
      <td class="fat">
       <table>
        <tr>
         <td class=middle><img src="$NicToolClient::image_dir/group.gif" alt="group"></td>
         <td class=middle> $zone->{'group_name'}</td>
        </tr>
       </table>
      </td>
     </tr>];

    if ( !$zone->{'pseudo'} ) {
        print qq[
     <tr class=light_grey_bg>
      <td class="nowrap"> With Permissions: </td>
      <td class="fat">
       <table> 
        <tr class=light_grey_bg>];
        my %perms = (
            'write'          => "Write",
            'delete'         => "Remove Delegation",
            'delegate'       => "Re-delegate",
            'add_records'    => "Add Records",
            'delete_records' => "Delete Records"
        );
        foreach ( qw/ write delete delegate add_records delete_records / ) {
            my $check = $zone->{"delegate_$_"} ? 'checked' : 'unchecked';
            print qq[
        <td><img src="$NicToolClient::image_dir/perm-$check.gif" alt="permssion $check">&nbsp; $perms{$_}</td>];
        }
        print qq[
        </tr>
       </table>
      </td>
     </tr>];
    }
    print qq[
   </table>
  </td>
 </tr>
</table>];
};

sub display_zone_delegation {
    my ( $nt_obj, $q, $user, $zone ) = @_;

    my $delegates = $nt_obj->get_zone_delegates( nt_zone_id => $zone->{nt_zone_id} );
    if ( $delegates->{error_code} ne 200 ) {
        warn "error get_zone_delegates: "
            . $delegates->{'error_code'} . " "
            . $delegates->{'error_msg'};
        return;
    }
    return if @{ $delegates->{'delegates'} } == 0;

    my $gid = $q->param('nt_group_id');
    my $per_link = $nt_obj->help_link('delperms');

    print qq[
<div id="zoneDelegateHeadline" class="dark_grey_bg bold side_pad">Zone Delegates</div>

<table id="zoneDelegationTable" class="fat">
 <tr id="delegateHeader" class="light_grey_bg fat">
  <td class="nowrap side_pad">Delegated To Group</td>
  <td class="nowrap side_pad">Delegated By</td>
  <td class="nowrap side_pad" colspan=3>Access Permissions $per_link</td>
 </tr>];

    foreach my $del ( @{ $delegates->{'delegates'} } ) {
        print qq[
 <tr class=light_grey_bg>
  <td class="nowrap middle side_pad"><a href="group.cgi?nt_group_id=$del->{'nt_group_id'}"> <img src="$NicToolClient::image_dir/group.gif" alt="group">$del->{'group_name'}</a> </td>
  <td class="nowrap middle side_pad"><a href="user.cgi?nt_user_id=$del->{'delegated_by_id'}"> <img src="$NicToolClient::image_dir/user.gif" alt="user"> $del->{'delegated_by_name'} </a> </td>
  <td class="nowrap side_pad">
    <img src="$NicToolClient::image_dir/perm-]
        . ( $del->{delegate_write} ? 'checked' : 'unchecked' )
        . qq[.gif" alt="">&nbsp;Write &nbsp;<img src="$NicToolClient::image_dir/perm-]
        . ( $del->{delegate_delete} ? "checked" : "unchecked" )
        . qq[.gif" alt="">&nbsp;Remove &nbsp;<img src="$NicToolClient::image_dir/perm-]
        . ( $del->{delegate_delegate} ? 'checked' : 'unchecked' )
        . qq[.gif" alt="">&nbsp;Re-delegate &nbsp;<img src="$NicToolClient::image_dir/perm-]
        . ( $del->{delegate_add_records} ? 'checked' : 'unchecked' )
        . qq[.gif" alt="">&nbsp;Add Records &nbsp;<img src="$NicToolClient::image_dir/perm-]
        . ( $del->{delegate_delete_records} ? 'checked' : 'unchecked' )
        . qq[.gif" alt="">&nbsp;Delete Records
  </td> 
  <td class="nowrap width1">];

        if ( !$zone->{'deleted'} && $user->{zone_delegate} ) {
            print qq[<a href="javascript:void window.open('delegate_zones.cgi?obj_list=$zone->{'nt_zone_id'}&amp;nt_group_id=$del->{'nt_group_id'}&amp;edit=1', 'delegate_win', 'width=640,height=480,scrollbars,resizable=yes')">Edit</a>];
        }
        else {
            print "<span class=disabled>Edit</span>";
        }
        print qq[
  </td> 
  <td class="nowrap center width1" title="Remove Delegation">];

        if ( !$zone->{'deleted'} && $user->{zone_delegate} ) {
            print qq[<a href="zone.cgi?nt_zone_id=$zone->{'nt_zone_id'}&amp;nt_group_id=$gid&amp;delegate_group_id=$del->{'nt_group_id'}&amp;deletedelegate=1" onClick="return confirm('Are you sure you want to remove the delegation of zone $zone->{'zone'} to group $del->{'group_name'}?');"><img src="$NicToolClient::image_dir/trash-delegate.gif" alt="Remove Delegation"></a>];
        }
        else {
            print qq[<img src="$NicToolClient::image_dir/trash-delegate-disabled.gif" alt="disabled">];
        }

        print qq[
  </td> 
 </tr>];
    }
    print qq[
</table>];
};

sub display_zone_properties {
    my ($nt_obj, $q, $zone, $user) = @_;

    my $state = 'nt_group_id=' . $q->param('nt_group_id');
    foreach ( @{ $nt_obj->paging_fields } ) {
        next if ! $q->param($_);
        $state .= "&amp;$_=" . $q->escape( $q->param($_) );
    }
    $state .= "&amp;nt_zone_id=$zone->{'nt_zone_id'}&amp;edit_zone=1";

    my $isdelegate = exists $zone->{'delegated_by_id'};

    print qq[
<div id="propertiesHeader" class="side_pad dark_grey_bg">
 <b>Properties</b>

 <ul class="menu_r">
  <li class=first id="zpHide" onClick="hideThis('zonePropertiesDiv'); hideThis('zpHide'); showMenuItem('zpShow')">Hide</li>
  <li class=first id="zpShow" style="display:none;" onClick="showThis('zonePropertiesDiv'); showMenuItem('zpHide'); hideThis('zpShow')">Show</li>];

    if ( !$zone->{'deleted'}
        && $user->{'zone_write'}
        && ( $isdelegate ? $zone->{'delegate_write'} : 1 ) )
    {
        print qq[
  <li><a href="zone.cgi?$state">Edit</a></li>];
    }
    else {
        print qq[
  <li class="disabled">Edit</li>];
    }
    print qq[
 </ul>
</div>

<div id="zonePropertiesDiv">
<table id="propertiesDetail" class="fat">
 <tr>
  <td class="width50">
   <table class="fat">];
    foreach ( qw/ zone mailaddr description serial minimum / ) {
        print qq[
    <tr class=light_grey_bg>
     <td class="nowrap pad2">$_: </td>
     <td class="fat pad2"> $zone->{$_} </td>
    </tr>],
    }
    print qq[
   </table>
  </td>
  <td class="width50 top">
   <table class="fat">];
    foreach ( qw/ refresh retry expire ttl / ) {
        print qq[
     <tr class=light_grey_bg>
      <td class="nowrap pad2">$_: </td>
      <td class="fat pad2"> $zone->{$_} </td>
     </tr>];
    }

    print qq[
   </table>
  </td>
 </tr>
</table>
</div>];
};

sub display_nameservers {
    my ( $nt_obj, $user, $q, $zone ) = @_;

    my $isdelegate = exists $zone->{'delegated_by_id'};

    my @fields = qw/ name address description /;

    print qq[
<div id="zoneNameservers" class="no_pad">
<div id="zoneNameserverHeader" class="dark_grey_bg no_margin">
  <span class="bold">Nameservers</span>
  <ul class="menu_r">
   <li class=first id="znsHide" onClick="hideThis('zoneNameserverListDiv'); hideThis('znsHide'); showMenuItem('znsShow')">Hide</li>
   <li class=first id="znsShow" style="display:none;" onClick="showThis('zoneNameserverListDiv'); showMenuItem('znsHide'); hideThis('znsShow')">Show</li>];

    if ( !$zone->{'deleted'} && $user->{'zone_write'}
        && ( $isdelegate ? $zone->{'delegate_write'} : 1 ) )
    {
        my $state = 'nt_group_id=' . $q->param('nt_group_id');
        foreach ( @{ $nt_obj->paging_fields } ) {
            next if ! $q->param($_);
            $state .= "&amp;$_=" . $q->escape( $q->param($_) );
        }
        $state .= "&amp;nt_zone_id=$zone->{'nt_zone_id'}&amp;edit_zone=1";
        print qq[<li><a href="zone.cgi?$state">Edit</a></li>];
    }
    else {
        print qq[<li class="disabled">Edit</li>];
    }
    print qq[
  </ul>
</div>
<div id="zoneNameserverListDiv">
 <table id="zoneNameserverList" class="pad1 fat">
  <tr class="dark_grey_bg pad2">
   <td class=center>name</td>
   <td class=center>address</td>
   <td class=center>description</td>
  </tr>];

    my $x = 1;
    foreach my $ns ( @{ $zone->{'nameservers'} } ) {
        my $bgcolor = $x++ % 2 == 0 ? 'light_grey_bg' : 'white_bg';
        print qq[
  <tr class="$bgcolor">
   <td><img class="no_pad" src="$NicToolClient::image_dir/nameserver.gif" alt="nameserver">$ns->{name}</td>
   <td>$ns->{address}</td>
   <td>$ns->{description}</td>
  </tr>];
    }

    print qq[
 </table>
</div>
</div>];
}

sub display_zone_records {
    my ( $nt_obj, $user, $q, $zone ) = @_;
    my $group = $nt_obj->get_group( nt_group_id => $user->{'nt_group_id'} );

    # process submitted form actions
    display_zone_records_new( $nt_obj, $user, $q, $zone );
    display_zone_records_edit( $nt_obj, $user, $q, $zone );
    display_zone_records_delete( $nt_obj, $q );

    my @columns = qw/ name type address ttl weight priority other description/;
    my %labels = (
        name        => 'Name',
        type        => 'Type',
        address     => 'Address',
        ttl         => 'TTL',
        weight      => 'Weight',
        priority    => 'Priority',
        other       => 'Port',
        description => 'Description',
    );

    if ( $q->param('edit_sortorder') ) {
        $nt_obj->display_sort_options( $q, \@columns, \%labels, 'zone.cgi',
            [ 'nt_group_id', 'nt_zone_id' ] );
    };
    if ( $q->param('edit_search') ) {
        $nt_obj->display_advanced_search( $q, \@columns, \%labels, 'zone.cgi',
            [ 'nt_group_id', 'nt_zone_id' ] );
    };

    my %params = ( nt_zone_id => $q->param('nt_zone_id') );
    my %sort_fields;
    $nt_obj->prepare_search_params( $q, \%labels, \%params, \%sort_fields, 50 );
    if ( ! %sort_fields ) {
        $sort_fields{'name'} = { 'order' => 1, 'mod' => 'Ascending' };
    };

    my $rv = $nt_obj->get_zone_records(%params);
    return $nt_obj->display_nice_error( $rv, "Get Zone Records" )
        if $rv->{'error_code'} != '200';

    my $zone_records = $rv->{'records'};

    my @state_fields;
    foreach ( @{ $nt_obj->paging_fields } ) {
        next if ! $q->param($_);
        push @state_fields, "$_=" . $q->escape( $q->param($_) );
    }
    my $state_string = join('&amp;', @state_fields);

# Display the RR header: Resource Records  New Resource Record | View Resource Record Log
    my $gid = $q->param('nt_group_id');
    my $zid = $q->param('nt_zone_id');
    my $options = qq[<li class=first><a href="zone_record_log.cgi?nt_group_id=$gid&amp;nt_zone_id=$zid">View Resource Record Log</a></li>
   ];

    my $zonedelegate = exists $zone->{'delegated_by_id'};
    my $has_dperm = $zonedelegate ? $zone->{'delegate_write'} && $zone->{'delegate_add_records'} : 1;
    if ( !$zone->{'deleted'} && $user->{'zonerecord_create'} && $has_dperm ) {
        $options .= qq[<li><a href="zone.cgi?nt_group_id=$gid&amp;nt_zone_id=$zid&amp;$state_string&amp;new_record=1#RECORD">New Resource Record</a></li>];
    }
    else {
        $options .= qq[<li class=disabled>New Resource Record</li>];
    }

    print qq[
<hr class="side_pad">
<div class="dark_grey_bg side_pad">
  <b>Resource Records</b>
  <ul class="menu_r">
    $options 
  </ul>
</div>];

    $nt_obj->display_search_rows( $q, $rv, \%params, 'zone.cgi', [ 'nt_group_id', 'nt_zone_id' ] );

    return if ! scalar @$zone_records;

    # show only columns used in the records in this zone
    @columns = qw(name type address ttl );

    my %has_type;
    foreach my $r_record (@$zone_records) {
        $has_type{ $r_record->{'type'} }++;
    }
    if ( $has_type{'MX'} || $has_type{'SRV'} ) {
        push @columns, 'weight';
    }
    if ( $has_type{'SRV'} ) {
        push @columns, 'priority', 'other';
    }
    push @columns, 'description';

    print qq[
<table id="zoneRecordTable" class="fat">
 <tr id="zoneRecordHeaderRow" class=dark_grey_bg>];

    foreach (@columns) {
        if ( $sort_fields{$_} ) {
            my $dir = uc( $sort_fields{$_}->{'mod'} ) eq 'ASCENDING' ? 'up' : 'down';
            print qq[
  <td class="dark_bg center">
     $labels{$_} &nbsp; &nbsp; $sort_fields{$_}->{'order'}
     <img src="$NicToolClient::image_dir/$dir.gif" alt="sort order">
  </td>];
        }
        else {
            print qq[\n  <td class=center>$labels{$_}</td>];
        }
    }
    print qq[
  <td class="center width1"></td>
  <td class="center width1"></td>
 </tr>];

    my $x = 0;
    my ( $isdelegate, $img );
    foreach my $r_record (@$zone_records) {
        $isdelegate = exists $r_record->{'delegated_by_id'};
        $img        = $isdelegate ? '-delegated' : '';
        $img        = "$NicToolClient::image_dir/r_record$img.gif";
        my $bgclass = $x++ % 2 == 0 ? 'light_grey_bg' : 'white_bg';
        my $hilite  = $x % 2 == 0 ? 'light_hilite_bg' : 'dark_hilite_bg';
        if ( $r_record->{'nt_zone_record_id'} eq $q->param('new_record_id') ) {
            $bgclass = $hilite;
        };
        print qq[
 <tr class=$bgclass>];

        $r_record->{name} = "@ ($zone->{'zone'})" if $r_record->{name} eq "@";

        if ( $r_record->{type} !~ /^MX|SRV$/i ) {
            $r_record->{weight} = '';
        }

        # shorten the max width of the address field (workaround for
        # display formatting problem with DomainKey entries.
        if ( length $r_record->{address} > 48 ) {
            my $max = 0;
            my @lines;
            while ( $max < length $r_record->{address} ) {
                push @lines, substr( $r_record->{address}, $max, 48 );
                $max += 48;
            }
            $r_record->{address} = join "<br>", @lines;
        }

        foreach (@columns) {
            if ( $_ eq 'name' ) {
                print qq[
  <td>];

                my $edit_url = "zone.cgi?$state_string&amp;nt_zone_record_id=$r_record->{'nt_zone_record_id'}&amp;nt_zone_id=$zone->{'nt_zone_id'}&amp;nt_group_id=$gid&amp;edit_record=1#RECORD";

                if ( !$zone->{'deleted'} ) {
                    print qq[<a href="$edit_url"><img src="$img" alt="rr"></a>];
                    print qq[<a href="$edit_url">$r_record->{$_}</a>];
                }
                else {
                    print qq[<img src="$img" alt="resource record">];
                    print $r_record->{$_};
                }

                if ( $r_record->{'delegated_by_id'} ) {
                    my $write = $r_record->{'delegate_write'} ? 'write' : 'nowrite';
                    print qq[&nbsp;&nbsp;<img src="$NicToolClient::image_dir/perm-$write.gif" alt="delegate write permission">];
                }
                print qq[
  </td>];
            }
            elsif ( $_ =~ /address|ttl|weight|priority|other/i ) {
                print qq[
  <td class="right"> $r_record->{$_} </td>];
            }
            else {
                print qq[
  <td class="center"> $r_record->{$_} </td>];
            }
        }
        print qq[
  <td class=center>];
        if ( !$zone->{'deleted'}
            && $group->{'has_children'}
            && $user->{'zonerecord_delegate'}
            && (  $isdelegate
                ? $r_record->{'delegate_delegate'}
                : ( $zonedelegate ? $zone->{'delegate_delegate'} : 1 )
            )
            )
        {
            print qq[<a href="javascript:void window.open('delegate_zones.cgi?type=record&amp;obj_list=$r_record->{'nt_zone_record_id'}&amp;nt_zone_id=$r_record->{'nt_zone_id'}', 'delegate_win', 'width=640,height=480,scrollbars,resizable=yes')">
    <img src="$NicToolClient::image_dir/delegate.gif" alt="Delegate Resource Record"></a></td>];
        }
        else {
            print qq[<img src="$NicToolClient::image_dir/delegate-disabled.gif" alt="delegate disabled"></td>];
        }

        if ( !$zone->{'deleted'}
            && $user->{'zonerecord_delete'}
            && !$isdelegate
            && ( $zonedelegate ? $zone->{'delegate_delete_records'} : 1 )
            )
        {
            print qq[
   <td class=center>
    <a href="zone.cgi?$state_string&amp;nt_zone_id=$zone->{'nt_zone_id'}&amp;nt_group_id=$gid&amp;nt_zone_record_id=$r_record->{'nt_zone_record_id'}&amp;delete_record=$r_record->{'nt_zone_record_id'}" onClick=\"return confirm('Are you sure you want to delete $zone->{'zone'} $r_record->{'type'} record $r_record->{'name'} that points to $r_record->{'address'} ?')">
    <img src="$NicToolClient::image_dir/trash.gif" alt="trash"></a></td>];

        }
        else {
            $img = $isdelegate ? '-delegate' : '';
            print qq[
   <td class=center><img src="$NicToolClient::image_dir/trash$img-disabled.gif" alt="disabled"></td>];
        }
        print qq[\n </tr>];
    }

    print qq[\n</table>];
}

sub display_zone_records_new {
    my ( $nt_obj, $user, $q, $zone ) = @_;

    return if ! $q->param('new_record');
    return if $q->param('Cancel');   # do nothing

    return display_edit_record( $nt_obj, $user, $q, '', $zone, 'new' )
        if ! $q->param('Create');

    my @fields = qw/ nt_group_id nt_zone_id name type address
                    weight priority other ttl description /;
    my %data;
    foreach my $x (@fields) {
        $data{$x} = $q->param($x);
    }

    my $error = $nt_obj->new_zone_record(%data);
    if ( $error->{'error_code'} != 200 ) {
        display_edit_record( $nt_obj, $user, $q, $error, $zone, 'new' );
        return;
    };

    $q->param(
            -name  => 'new_record_id',
            -value => $error->{'nt_zone_record_id'}
            );
    $nt_obj->display_nice_message(
            "New Zone Record '$data{name}' Created", "New Zone Record" );
};

sub display_zone_records_edit {
    my ( $nt_obj, $user, $q, $zone ) = @_;

    return if ! $q->param('edit_record');
    return if $q->param('Cancel'); # do nothing

    return display_edit_record( $nt_obj, $user, $q, "", $zone, 'edit' )
        if ! $q->param('Save');

    my @fields = qw( nt_group_id nt_zone_id nt_zone_record_id name type
            address weight priority other ttl description deleted );
    my %data;
    foreach my $x (@fields) {
        $data{$x} = $q->param($x);
    }
    my $error = $nt_obj->edit_zone_record(%data);
    if ( $error->{'error_code'} != 200 ) {
        display_edit_record( $nt_obj, $user, $q, $error, $zone, 'edit' );
        return;
    }
    $nt_obj->display_nice_message(
            "Zone Record successfully modified.", "Edit Zone Record" );
};

sub display_zone_records_delete {
    my ( $nt_obj, $q ) = @_;

    return if ! $q->param('delete_record');

    my $error = $nt_obj->delete_zone_record(
        nt_group_id       => $q->param('nt_group_id'),
        nt_zone_record_id => $q->param('nt_zone_record_id')
    );

    if ( $error->{'error_code'} != 200 ) {
        $nt_obj->display_nice_error( $error, "Delete Zone Record" );
    }
    else {
        $nt_obj->display_nice_message(
            "Zone Record successfully deleted.",
            "Delete Zone Record" );
    }
};

sub display_edit_record {
    my ( $nt_obj, $user, $q, $message, $zone, $edit ) = @_;

    my $zone_record = { 'ttl' => $NicToolClient::default_zone_record_ttl };
    my $action = 'New';
    my $message2;

    # is this a Save or Edit operation?
    if ( $q->param('nt_zone_record_id') && !$q->param('Save') ) {

        if ( $q->param('nt_zone_record_log_id') ) {
            $action      = 'Recover';
            $zone_record = $nt_obj->get_zone_record_log_entry(
                nt_zone_record_id     => $q->param('nt_zone_record_id'),
                nt_zone_record_log_id => $q->param('nt_zone_record_log_id')
            );
        }
        else {
            $action      = 'Edit';
            $zone_record = $nt_obj->get_zone_record(
                nt_group_id       => $q->param('nt_group_id'),
                nt_zone_id        => $q->param('nt_zone_id'),
                nt_zone_record_id => $q->param('nt_zone_record_id')
            );
        }

        if ( $zone_record->{'error_code'} != 200 ) {
            $message2 = $zone_record;
        }
        else {
            $zone_record->{'name'} = $zone->{'zone'} . "."
                if ( $zone_record->{'name'} eq "@" && $zone->{'zone'} );
            $zone_record->{'address'} = $zone->{'zone'} . "."
                if ( $zone_record->{'address'} eq "@" && $zone->{'zone'} );
        }
    }
    my $isdelegate = exists $zone_record->{'delegated_by_id'};
    my $pseudo     = $zone_record->{'pseudo'};

    my ( $type_values, $type_labels );

    my $rr_types = $nt_obj->rr_types;
    my %forwards = map { $_->{name} => "$_->{description} ($_->{name})" } 
        grep( $_->{forward} == 1, @$rr_types);
    my %reverse  = map { $_->{name} => "$_->{description} ($_->{name})" } 
        grep( $_->{reverse} == 1, @$rr_types);

    # present RR types appropriate for the type of zone
    if ( $zone->{'zone'} =~ /(in-addr|ip6)\.arpa$/ ) {
        $type_values = [ sort keys %reverse ];
        $type_labels = \%reverse;
    }
    else {
        $type_values = [ sort keys %forwards ];
        $type_labels = \%forwards;
    }

    # does user have Edit permissions?
    my $modifyperm = !$isdelegate && $user->{'zonerecord_write'}
        || $isdelegate
        && $user->{'zonerecord_write'}
        && $zone_record->{'delegate_write'};

    if ($modifyperm) {
        print qq[
<form method="post" action="zone.cgi" name="rr_edit">],
            $q->hidden( -name => $edit . '_record' ), "\n",
            $q->hidden( -name => 'nt_group_id' ), "\n",
            $q->hidden( -name => 'nt_zone_id' ), "\n";
        print $q->hidden( -name => 'nt_zone_record_id' ) if $edit eq 'edit';
        print $q->hidden( -name => 'nt_zone_record_log_id' ), "\n";
        print $q->hidden( -name => 'deleted', -value => 0 ) if $action eq 'Recover';

        foreach ( @{ $nt_obj->paging_fields } ) {
            print $q->hidden( -name => $_ ), "\n";
        }
    }
    else {
        $action = 'View' if $action eq 'Edit';
    }

    $nt_obj->display_nice_error($message)  if $message;
    $nt_obj->display_nice_error($message2) if $message2;
    print qq[
<a name="RECORD" id="RECORD"></a>
<div class="dark_bg">Resource Record</div>];

    # display delegation information
    if ( !$isdelegate && $edit ne 'new' ) {
        my $delegates = $nt_obj->get_zone_record_delegates(
            nt_zone_record_id => $zone_record->{'nt_zone_record_id'} );
        if ( $delegates->{error_code} ne 200 ) {
            warn
                "error get_zone_record_delegates(nt_zone_record_id=>$zone_record->{'nt_zone_record_id'}: "
                . $delegates->{'error_code'} . " "
                . $delegates->{'error_msg'};
        }
        elsif ( @{ $delegates->{'delegates'} } gt 0 ) {
            display_edit_record_delegates( $nt_obj, $q, $user, $zone_record, $delegates  );
        }
    }
    elsif ( $edit ne 'new' && !$pseudo ) {
        display_new_record_delegates( $user, $zone_record, $q );
    };

    print qq[
<table class="fat">
 <tr class="dark_grey_bg"><td colspan=2> $action </td></tr>
 <tr class="light_grey_bg">
  <td class="right"> Name:</td>
  <td class="fat">], 
        $modifyperm ? $q->textfield(
        -name      => 'name',
        -size      => 40,
        -maxlength => 127,
        -default   => $zone_record->{'name'}
        ) : $zone_record->{'name'},
        ( $zone_record->{'name'} ne "$zone->{'zone'}." ? "<b>.$zone->{'zone'}.</b>" : ""),
        qq[
  </td>
 </tr>];

    my $default_record_type = $zone_record->{'type'};
    $default_record_type = 'PTR' if ( $zone->{'zone'} =~ /(in-addr|ip6)\.arpa/ );

    print qq[
 <tr class="light_grey_bg">
  <td class=right> Type:</td>
  <td class="fat">], 
        $modifyperm ? $q->popup_menu(
            -name    => 'type',
            -id      => 'rr_type',
            -values  => $type_values,
            -labels  => $type_labels,
            -default => $default_record_type,
            -onClick => "showFieldsForRRtype(value)",
# not valid for popup menus (according to CGI.pm docs), but works
            -onChange => "showFieldsForRRtype(value)",    # seems to work
            -onFocus  => "showFieldsForRRtype(value)",
# run, darn it, even if user doesn't change value and onClick isn't permitted
        )
        : $type_labels->{ $zone_record->{'type'} }, qq[
  </td>
 </tr>
 <tr class="light_grey_bg">
  <td class="right"> Address:</td>
  <td style="width:100%;">], $modifyperm
        ? $q->textfield(
        -name      => 'address',
        -size      => 50,
        -maxlength => 255,
        -default   => $zone_record->{'address'},
        )
        : $zone_record->{'address'},
        $nt_obj->help_link('rraddress') . qq[
  </td>
 </tr>
 <tr id="tr_weight" class="light_grey_bg">
  <td class="right"> Weight:</td>
  <td class="fat">], $modifyperm ? $q->textfield(
        -name      => 'weight',
        -size      => 5,
        -maxlength => 10,
        -default   => '10',
        -default   => $zone_record->{'weight'}
        )
        : $zone_record->{'weight'},
        qq[
  </td>
 </tr>
 <tr id="tr_priority" class="light_grey_bg">
  <td class="right"> Priority:</td>
  <td class="fat">], $modifyperm
        ? $q->textfield(
        -name      => 'priority',
        -size      => 5,
        -maxlength => 10,
        -default   => '10',
        -default   => $zone_record->{'priority'}
        )
        : $zone_record->{'priority'}, qq[
  </td>
 </tr>
 <tr id="tr_other" class="light_grey_bg">
  <td class="right"> Port:</td>
  <td class="fat">], $modifyperm ? $q->textfield(
        -name      => 'other',
        -size      => 5,
        -maxlength => 10,
        -default   => '10',
        -default   => $zone_record->{'other'}
        )
        : $zone_record->{'other'},
        qq[
  </td>
 </tr>
 <tr class="light_grey_bg">
  <td class="right"> TTL:</td>
  <td class="fat">], $modifyperm ? $q->textfield(
        -name      => 'ttl',
        -size      => 5,
        -maxlength => 10,
        -default   => $zone_record->{'ttl'}
        )
        : $zone_record->{'ttl'}, qq[
  </td>
 </tr>
 <tr class="light_grey_bg">
  <td class="right"> Description:</td>
  <td class="fat">], $modifyperm ? $q->textfield(
        -name      => 'description',
        -size      => 60,
        -maxlength => 128,
        -default   => $zone_record->{'description'}
        )
        : $zone_record->{'description'} || "&nbsp;",
        qq[
  </td>
 </tr>
 <tr class="dark_grey_bg">
  <td colspan="2" class="center">],
        $modifyperm ? $q->submit( $edit eq 'edit' ? 'Save' : 'Create' )
        . $q->submit('Cancel')
        : '&nbsp;', qq[
  </td>
 </tr>
</table>

<script>
\$(document).ready(function(){
  showFieldsForRRtype('$default_record_type');
});
</script>];

    print $q->end_form if $modifyperm;
}

sub display_edit_record_delegates {
    my ($nt_obj, $q, $user, $zone_record, $delegates  ) = @_;

    print qq[
<table class="fat"><tr class=dark_grey_bg><td>Delegates</td></tr></table>
<table class="fat no_pad">
 <tr>
  <td class="top">
   <table class="fat">
    <tr class=light_grey_bg>
     <td class="nowrap"> Group</td>
     <td class="nowrap"> Delegated By</td>
     <td class="nowrap"> Access Permissions $nt_obj->help_link('delperms') </td>
     <td class="nowrap width1"> Edit</td>
     <td class="nowrap center width1"><img src="$NicToolClient::image_dir/trash-delegate.gif" alt="trash delegate"></td>
    </tr>
];
    foreach my $del ( @{ $delegates->{'delegates'} } ) {
        print qq[
    <tr class=light_grey_bg>
     <td class="nowrap center">
      <table>
       <tr>
        <td class="middle"><a href="group.cgi?nt_group_id=$del->{'nt_group_id'}"><img src="$NicToolClient::image_dir/group.gif" alt="group"></a></td>
        <td class="middle"><a href="group.cgi?nt_group_id=$del->{'nt_group_id'}">$del->{'group_name'}</a></td>
       </tr>
      </table>
     </td>
     <td class="nowrap center">
      <table>
       <tr>
        <td class="middle"><a href="user.cgi?nt_user_id=$del->{'delegated_by_id'}">
        <img src="$NicToolClient::image_dir/user.gif" alt=""></a></td>
        <td class="middle"><a href="user.cgi?nt_user_id=$del->{'delegated_by_id'}">$del->{'delegated_by_name'}</a></td>
       </tr>
      </table>
     </td>
     <td class="nowrap">
       <table>
        <tr>
         <td><img src="$NicToolClient::image_dir/perm-]
            . ( $del->{delegate_write} ? 'checked' : 'unchecked' )
            . qq(.gif" alt="write perm">&nbsp;Write</td><td><img src="$NicToolClient::image_dir/perm-)
            . ( $del->{delegate_delete} ? 'checked' : 'unchecked' )
            . qq(.gif" alt="delete perm">&nbsp;Remove</td><td><img src="$NicToolClient::image_dir/perm-)
            . ( $del->{delegate_delegate} ? 'checked' : 'unchecked' )
            . qq[.gif" alt="re-delegate perm">&nbsp;Re-delegate</td>
        </tr>
       </table>
     </td>
     <td class="nowrap width1">];

        if ( $user->{zonerecord_delegate} ) {
            print qq[<a href="javascript:void window.open('delegate_zones.cgi?type=record&amp;obj_list=$zone_record->{'nt_zone_record_id'}&amp;nt_zone_id=$zone_record->{'nt_zone_id'}&amp;nt_group_id=$del->{'nt_group_id'}&amp;edit=1', 'delegate_win', 'width=640,height=480,scrollbars,resizable=yes')">Edit</a>];
        }
        else {
            print qq[<span class=disabled>Edit</span>];
        }
        print qq[ 
     </td>
     <td class="nowrap center width1">];

        if ( $user->{zonerecord_delegate} ) {
            my $gid = $q->param('nt_group_id');
            print qq[<a href="zone.cgi?type=record&amp;nt_zone_record_id=$zone_record->{'nt_zone_record_id'}&amp;nt_zone_id=$zone_record->{'nt_zone_id'}&amp;nt_group_id=$gid&amp;delegate_group_id=$del->{'nt_group_id'}&amp;deletedelegate=1" onClick="return confirm('Are you sure you want to remove the delegation of resource record $zone_record->{'name'} to group $del->{'group_name'}?');"><img src="$NicToolClient::image_dir/trash-delegate.gif" alt="Remove Delegation"></a>];
            }
            else {
                print qq[<img src="$NicToolClient::image_dir/trash-delegate-disabled.gif" alt="trash delegate disabled">];
            }

            print qq[
     </td>
    </tr>];
    }
    print qq[ 
   </table> 
  </td>
 </tr>
</table>];
};

sub display_new_record_delegates {
    my ($user, $zone_record, $q  ) = @_;

    my $gid = $q->param('nt_group_id');
    print qq[
<div class="dark_grey_bg side_pad"> <b>Delegation</b> </div>

<table class="fat">
 <tr> 
  <td class=top>
   <table class="fat">
    <tr class=light_grey_bg>
     <td class="nowrap"> Delegated by: </td>
     <td class="fat"> 
      <table> 
       <tr>
        <td class=middle><img src="$NicToolClient::image_dir/user.gif" alt="user"></td>
        <td class=middle> $zone_record->{'delegated_by_name'}</td>
       </tr>
      </table>
     </td>
    </tr>
    <tr class=light_grey_bg>
     <td class="nowrap"> Belonging to group: </td>
     <td class="fat"> 
      <table> 
       <tr>
        <td class=middle><img src="$NicToolClient::image_dir/group.gif" alt="group"></td>
        <td class=middle> $zone_record->{'group_name'}</td>
       </tr> 
      </table>
     </td>
    </tr>

    <tr class=light_grey_bg>
     <td class="nowrap"> With Permissions: </td>
     <td class="fat">
      <table>
       <tr class=light_grey_bg>];

    my %perms = (
        'write'  => "Write",
        'delete' => "Remove Delegation",
        delegate => "Re-delegate"
    );
    foreach (qw(write delete delegate)) {
        print qq[<td><img src="$NicToolClient::image_dir/perm-];
        print "un" if ! $zone_record->{"delegate_$_"};
        print qq[checked.gif" alt="delegate perm">&nbsp; $perms{$_} </td>];
    }
    print qq[</tr>
      </table>
     </td>
    </tr>
   </table>

  </td>
 </tr>
</table>

<table class="fat"> <tr class=dark_grey_bg> <td> Actions</td> </tr> </table>

<table class="fat">
 <tr class=light_grey_bg>
  <td class=left> ];
    if (   $user->{'zonerecord_delegate'}
        && $zone_record->{'delegate_delete'} )
    {
        print qq[<a href="zone.cgi?type=record&amp;nt_zone_record_id=$zone_record->{'nt_zone_record_id'}&amp;nt_zone_id=$zone_record->{'nt_zone_id'}&amp;nt_group_id=$gid&amp;delegate_group_id=$gid&amp;deletedelegate=1" onClick="return confirm('Are you sure you want to remove the delegation of resource record $zone_record->{'name'} to group $zone_record->{'group_name'}?');">Remove Delegation</a>];
    }
    else {
        print "<span class=disabled>Remove Delegation</span>";
    }
    print " | ";

    if (   $user->{zone_write}
        && $user->{'zonerecord_delegate'}
        && $zone_record->{'delegate_delegate'} )
    {
        print qq[<a href="javascript:void window.open('delegate_zones.cgi?type=record&amp;obj_list=$zone_record->{'nt_zone_record_id'}&amp;nt_zone_id=$zone_record->{'nt_zone_id'}', 'delegate_win', 'width=640,height=480,scrollbars,resizable=yes')">Re-Delegate</a>];
    }
    else {
        print "<span class=disabled>Re-Delegate</span>";
    }
    print qq[
  </td>
 </tr>
</table>];
}

sub display_edit_zone {
    my ( $nt_obj, $user, $q, $message, $zone, $edit ) = @_;

    my $action;

    print $q->start_form(
        -action => 'zone.cgi',
        -method => 'POST',
        -name   => 'new_zone'
    );
    print $q->hidden( -name => 'nt_group_id' );
    print $q->hidden( -name => 'nt_zone_id' ) if $edit eq 'edit';
    print $q->hidden( -name => $edit . '_zone' );

    if ( $q->param('undelete') && $zone->{'deleted'} ) {
        $action = 'Recover';
        print $q->hidden( -name => 'undelete' );

    }
    else {
        $action = 'Edit';
    }

    foreach ( @{ $nt_obj->paging_fields() } ) {
        print $q->hidden( -name => $_ ) if ( $q->param($_) );
    }

    $nt_obj->display_nice_error($message) if $message;

    print qq[<a name="ZONE"></a>
<table class="fat">
 <tr class=dark_bg><td colspan=2 class="bold">$action Zone</td></tr>
 <tr class=light_grey_bg>
  <td class=right>Zone:</td>
  <td class="fat">$zone->{'zone'}</td></tr>
 <tr class=light_grey_bg>
  <td class="right top">Nameservers:</td>
  <td class="width80">\n];

    my %zone_ns = map { $_->{'nt_nameserver_id'}, 1 } @{ $zone->{'nameservers'} };

    # get list of available nameservers
    my $ns_tree = $nt_obj->get_usable_nameservers(
        nt_group_id => $q->param('nt_group_id'),
    );

    foreach ( 1 .. scalar( @{ $ns_tree->{'nameservers'} } ) ) {

        my $ns = $ns_tree->{'nameservers'}->[ $_ - 1 ];

        print $q->checkbox(
            -name    => "nameservers",
            -checked => ( $zone_ns{ $ns->{'nt_nameserver_id'} } ? 1 : 0 ),
            -value   => $ns->{'nt_nameserver_id'},
            -label   => "$ns->{'description'} ($ns->{'name'})"
            ),
            "<BR>";
        delete $zone_ns{ $ns->{'nt_nameserver_id'} };
    }
    if ( @{ $ns_tree->{'nameservers'} } == 0 ) {
        print "No available nameservers.";
    }
    foreach ( keys %zone_ns ) {
        my $ns = $nt_obj->get_nameserver( nt_nameserver_id => $_ );
        print "<li>$ns->{'description'} ($ns->{'name'})<BR>";
    }
    print qq[</td>
 </tr>];

    print qq[
 <tr class=light_grey_bg>
  <td class="right top">Description:</td>
  <td class="width80">],
        $q->textarea(
        -name      => 'description',
        -cols      => 50,
        -rows      => 4,
        -maxlength => 255,
        -default   => $zone->{'description'}
        ),
        qq[</td>
 </tr>
 <tr class=light_grey_bg>
  <td class=right>TTL:</td>
  <td class="width80">],
        $q->textfield(
        -name      => 'ttl',
        -size      => 8,
        -maxlength => 10,
        -default   => $zone->{'ttl'}
        ),
    qq[<input type="button" value="Default" onClick="this.form.ttl.value=$NicToolClient::default_zone_ttl"> $NicToolClient::default_zone_ttl </td>
 </tr>
 <tr class=light_grey_bg>
  <td class=right>Refresh:</td>
  <td class="width80">],
        $q->textfield(
        -name      => 'refresh',
        -size      => 8,
        -maxlength => 10,
        -default   => $zone->{'refresh'}
        ),
        qq[<input type="button" value="Default" onClick="this.form.refresh.value=$NicToolClient::default_zone_refresh"> $NicToolClient::default_zone_refresh</td>
 </tr>
 <tr class=light_grey_bg>
  <td class=right>Retry:</td>
  <td class="width80">],
        $q->textfield(
        -name      => 'retry',
        -size      => 8,
        -maxlength => 10,
        -default   => $zone->{'retry'}
        ),
        qq[<input type="button" value="Default" onClick="this.form.retry.value=$NicToolClient::default_zone_retry"> $NicToolClient::default_zone_retry</td>
 </tr>
 <tr class=light_grey_bg>
  <td class=right>Expire:</td>
  <td class="width80">],
        $q->textfield(
        -name      => 'expire',
        -size      => 8,
        -maxlength => 10,
        -default   => $zone->{'expire'}
        ),
        qq[<input type="button" value="Default" onClick="this.form.expire.value=$NicToolClient::default_zone_expire"> $NicToolClient::default_zone_expire</td>
 </tr>
 <tr class=light_grey_bg>
  <td class=right>Minimum:</td>
  <td class="width80">],
        $q->textfield(
        -name      => 'minimum',
        -size      => 8,
        -maxlength => 10,
        -default   => $zone->{'minimum'}
        ),
        qq[<input type="button" value="Default" onClick="this.form.minimum.value=$NicToolClient::default_zone_minimum"> $NicToolClient::default_zone_minimum</td>
 </tr>
 <tr class=light_grey_bg>
  <td class=right>MailAddr:</td>
  <td class="width80">],
        $q->textfield(
        -name      => 'mailaddr',
        -size      => 25,
        -maxlength => 255,
        -default   => $zone->{'mailaddr'},
        ),
        qq[<input type="button" value="Default" onClick="this.form.mailaddr.value='hostmaster.$zone->{'zone'}'"> hostmaster.$zone->{'zone'}.],
        qq[</td>
 </tr>
 <tr class=dark_grey_bg>
  <td colspan=2 class=center>],
        $q->submit( $edit eq 'edit' ? 'Save' : 'Create' ),
        $q->submit('Cancel'), qq[</td></tr>
</table>],
        $q->end_form;
}

